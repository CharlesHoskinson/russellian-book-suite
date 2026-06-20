import pytest
pytestmark = pytest.mark.windows_canary
import json
from pathlib import Path
from scripts.concept_ledger import build_concept_ledger, _norm, _slug, harvest_title_case


def _ws(tmp_path: Path, chapters: dict[str, str]) -> Path:
    ws = tmp_path / "ws"
    for cid, body in chapters.items():
        d = ws / "chapters" / "drafts" / cid
        d.mkdir(parents=True)
        (d / "draft.md").write_text(body, encoding="utf-8")
    (ws / "references").mkdir(parents=True, exist_ok=True)
    return ws


def test_harvest_title_case_finds_multiword_devices():
    got = harvest_title_case("The Authority Airgap separates power. The Bounded Polis follows.")
    assert "Authority Airgap" in got
    assert "Bounded Polis" in got
    assert "The Authority Airgap" not in got
    assert "The Bounded Polis" not in got
    assert sorted(got) == ["Authority Airgap", "Bounded Polis"]


def test_harvest_title_case_keeps_hyphenated_term():
    got = harvest_title_case(
        "The Self-Sovereign Identity model recurs. Self-Sovereign Identity again."
    )
    assert "Self-Sovereign Identity" in got
    assert "Sovereign Identity" not in got


def test_slug_collisions_distinct_and_nonempty(tmp_path):
    ws = _ws(tmp_path, {
        "ch-01": "# C1\nWe write code in C++ here.\n",
        "ch-02": "# C2\nWe also write code in C# here.\n",
    })
    seed = ws / "references" / "seed-concepts.txt"
    seed.write_text("C++\nC#\n", encoding="utf-8")
    out = build_concept_ledger(ws, seed_path=seed)
    recs = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    slugs = [r["slug"] for r in recs]
    assert all(s for s in slugs)
    assert len(slugs) == len(set(slugs))


def test_source_stamps_seed_and_harvested(tmp_path):
    ws = _ws(tmp_path, {
        "ch-01": "# C1\nCall that separation the Authority Airgap.\n",
        "ch-02": "# C2\nThe Bounded Polis recurs here.\n",
        "ch-03": "# C3\nThe Bounded Polis appears again.\n",
    })
    seed = ws / "references" / "seed-concepts.txt"
    seed.write_text("Authority Airgap\n", encoding="utf-8")
    out = build_concept_ledger(ws, seed_path=seed)
    recs = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    air = next(r for r in recs if r["slug"] == "authority-airgap")
    polis = next(r for r in recs if r["slug"] == "bounded-polis")
    assert air["source"] == "seed"
    assert polis["source"] == "harvested"


def test_seed_concept_introduced_in_earliest_chapter(tmp_path):
    ws = _ws(tmp_path, {
        "ch-01": "# C1\nIntelligence is not enough.\n",
        "ch-07": "# C7\nCall that separation the Authority Airgap.\n",
        "ch-09": "# C9\nThe airgap also gives a court.\n",
    })
    seed = ws / "references" / "seed-concepts.txt"
    seed.write_text("Authority Airgap | the airgap\n", encoding="utf-8")
    out = build_concept_ledger(ws, seed_path=seed)
    recs = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    air = next(r for r in recs if r["slug"] == "authority-airgap")
    assert air["introduced_in"] == "ch-07"
    assert air["intro_n"] == 7
    assert "the airgap" in air["aliases"]


def test_norm_lowercases_and_collapses():
    assert _norm("  The  Airgap ") == "the airgap"
