"""Tests for synthesize_exemplars.py."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compile_thesis import compile_thesis  # noqa: E402
from synthesize_exemplars import build_pack, synthesize_exemplars  # noqa: E402

FIXTURE_THESIS = Path(__file__).parent / "fixtures" / "tiny-thesis.yaml"
REQUIRED_FIELDS = {
    "supports_node",
    "supports_statement",
    "claim_id",
    "claim_statement",
    "exemplar_paragraph",
}


def _claim(claim_id: str, text: str, chapters: list[str]) -> dict:
    return {
        "claim_id": claim_id,
        "canonical_text": text,
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "src-a", "locator_text": "x"}],
        "created_at": "2026-05-11T00:00:00Z",
        "supports_chapters": chapters,
    }


def _make_workspace(tmp_path: Path, claim_count: int = 12) -> Path:
    """Lay out a workspace: thesis YAML + compiled triples + claim ledger."""
    workspace = tmp_path / "book"
    (workspace / "thesis").mkdir(parents=True)
    shutil.copy(FIXTURE_THESIS, workspace / "thesis" / "tiny.yaml")
    compile_thesis(workspace, "tiny")

    (workspace / ".knowledge").mkdir(exist_ok=True)
    ledger = workspace / ".knowledge" / "claims.jsonl"
    rows = []
    for i in range(claim_count):
        chapters = ["ch-01"] if i % 2 == 0 else ["ch-02"]
        rows.append(_claim(
            claim_id=f"clm-2026-{i:06d}",
            text=f"Synthetic fact number {i} stands without qualification",
            chapters=chapters,
        ))
    ledger.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    return workspace


def test_emits_expected_count(tmp_path: Path) -> None:
    """A fixture chapter produces 8-12 exemplars."""
    workspace = _make_workspace(tmp_path, claim_count=14)
    pack = build_pack(workspace, "ch-01")
    assert 8 <= len(pack["exemplars"]) <= 12, (
        f"got {len(pack['exemplars'])} exemplars; expected 8-12"
    )
    assert pack["chapter_id"] == "ch-01"
    assert "first-leg" in pack["advances_sub_arguments"]
    out_path = synthesize_exemplars(workspace, "ch-01")
    assert out_path == workspace / ".exemplars" / "ch-01.json"
    on_disk = json.loads(out_path.read_text(encoding="utf-8"))
    assert 8 <= len(on_disk["exemplars"]) <= 12


def test_exemplar_shape(tmp_path: Path) -> None:
    """Each exemplar JSON entry has all required fields and the SYNTHETIC tag."""
    workspace = _make_workspace(tmp_path, claim_count=10)
    pack = build_pack(workspace, "ch-02")
    assert pack["exemplars"], "pack must contain at least one exemplar"
    for ex in pack["exemplars"]:
        missing = REQUIRED_FIELDS - ex.keys()
        assert not missing, f"exemplar missing fields: {missing}"
        assert ex["synthetic"] is True
        assert ex["supports_node"]
        assert ex["claim_id"].startswith("clm-")
        assert "[SYNTHETIC]" in ex["exemplar_paragraph"]
        assert ex["claim_id"] in ex["exemplar_paragraph"]
        # Paragraph ends with terminal punctuation
        assert ex["exemplar_paragraph"].rstrip().endswith((".", "!", "?"))
    assert pack["house_style_notes"]


def test_missing_thesis_raises(tmp_path: Path) -> None:
    workspace = tmp_path / "book"
    workspace.mkdir()
    with pytest.raises(FileNotFoundError):
        build_pack(workspace, "ch-01")


def test_load_claims_skips_corrupt_ledger_line(tmp_path: Path) -> None:
    """4.2: a malformed JSONL line must not crash exemplar synthesis."""
    workspace = _make_workspace(tmp_path, claim_count=6)
    with (workspace / ".knowledge" / "claims.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("{ corrupt json line\n")
    pack = build_pack(workspace, "ch-01")  # must not raise
    assert pack["exemplars"]
