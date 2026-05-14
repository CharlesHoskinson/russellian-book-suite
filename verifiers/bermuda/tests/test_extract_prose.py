from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.extract_prose import extract_chapter, extract_release


def test_extracts_clean_chapter(fixtures_dir: Path, tmp_work: Path) -> None:
    atoms = extract_chapter(fixtures_dir / "chapter_clean.md")
    assert any(a["predicate"] == ":parishes-count" and a["value"] == 9 for a in atoms)


def test_extracts_drifty_chapter(fixtures_dir: Path) -> None:
    atoms = extract_chapter(fixtures_dir / "chapter_with_8_parishes.md")
    # Should pick up BOTH the "8 parishes" and the "9" mention — the verifier
    # decides which contradicts the canonical
    values = sorted(a["value"] for a in atoms if a["predicate"] == ":parishes-count")
    assert values == [8, 9]


def test_extract_release_walks_chapter_bundles(tmp_path: Path) -> None:
    bundles = tmp_path / "chapter-bundles"
    bundles.mkdir()
    (bundles / "ch-01").mkdir()
    (bundles / "ch-01" / "draft.md").write_text("Bermuda has 181 named islands and rocks.")
    (bundles / "ch-02").mkdir()
    (bundles / "ch-02" / "draft.md").write_text("Bermuda has 8 parishes.")
    n = extract_release(bundles, tmp_path / "prose-facts.edn")
    payload = json.loads((tmp_path / "prose-facts.edn").read_text(encoding="utf-8"))
    assert n == 2
    chapters = {a["source"]["file"] for a in payload["atoms"]}
    assert "ch-01/draft.md" in str(chapters) or any("ch-01" in c for c in chapters)


def test_pass_b_calls_llm_and_parses_json() -> None:
    from scripts.extract_prose import extract_pass_b

    def fake_llm(prompt: str) -> str:
        return json.dumps([
            {"predicate": ":parishes-count", "subject": ":Bermuda", "value": 9},
            {"predicate": ":population", "subject": ":Bermuda", "value": 64000},
        ])

    atoms = extract_pass_b("Some chapter text.", source_file="ch-01.md",
                           llm_call=fake_llm)
    assert len(atoms) == 2
    assert any(a["predicate"] == ":parishes-count" for a in atoms)
    assert all(a["extractor"] == "llm" for a in atoms)
    assert all(a["confidence"] == 0.6 for a in atoms)


def test_pass_b_handles_malformed_llm_output() -> None:
    from scripts.extract_prose import extract_pass_b

    def fake_llm(prompt: str) -> str:
        return "not json"

    atoms = extract_pass_b("text", source_file="ch.md", llm_call=fake_llm)
    assert atoms == []


def test_extract_release_with_pass_b_enabled(tmp_path: Path) -> None:
    from scripts.extract_prose import extract_release

    bundles = tmp_path / "chapter-bundles"
    (bundles / "ch-01").mkdir(parents=True)
    (bundles / "ch-01" / "draft.md").write_text("Bermuda has 9 parishes.")

    def fake_llm(prompt: str) -> str:
        return json.dumps([
            {"predicate": ":population", "subject": ":Bermuda", "value": 64000},
        ])

    n = extract_release(bundles, tmp_path / "prose-facts.edn",
                        llm_call=fake_llm)
    payload = json.loads((tmp_path / "prose-facts.edn").read_text(encoding="utf-8"))
    # Pass A finds parishes, Pass B finds population → 2 atoms
    assert n == 2
