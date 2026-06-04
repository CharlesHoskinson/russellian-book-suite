"""Tests for dispatch_entailment.py."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dispatch_entailment import write_payloads, scan_paragraphs  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
THESIS_TTL = FIXTURES / "datalog_thesis.ttl"
MANUSCRIPT_MD = FIXTURES / "manuscript-entailment.md"
LEDGER_JSONL = FIXTURES / "ledger-entailment.jsonl"

VERSION = "v0.1.0"

REQUIRED_FIELDS = {
    "paragraph",
    "supports_node",
    "supports_statement",
    "cited_claim",
    "sibling_nodes",
    "expected_response",
    "meta",
}


def _build_workspace(tmp_path: Path) -> Path:
    """Lay out a fake workspace with the three input artefacts in place."""
    (tmp_path / ".knowledge").mkdir()
    shutil.copy(THESIS_TTL, tmp_path / ".knowledge" / "thesis-triples.ttl")
    release_dir = tmp_path / "book" / "releases" / VERSION
    release_dir.mkdir(parents=True)
    shutil.copy(MANUSCRIPT_MD, release_dir / "manuscript.md")
    (tmp_path / "claims").mkdir()
    shutil.copy(LEDGER_JSONL, tmp_path / "claims" / "ledger.jsonl")
    return tmp_path


def test_scan_paragraphs_skips_footnote_definitions() -> None:
    md = (
        "# Chapter 1\n\n"
        "<!-- supports: first-leg -->\n"
        "A genuine paragraph with enough words to count as prose.\n\n"
        "[^a]: A footnote definition that must not be scanned as a paragraph.\n"
    )
    texts = [p.text for p in scan_paragraphs(md)]
    assert any("genuine paragraph" in t for t in texts)
    assert not any(t.lstrip().startswith("[^a]") for t in texts)


def test_emits_one_payload_per_paragraph(tmp_path: Path) -> None:
    """Three carriers in the manuscript yield three payloads + an index."""
    workspace = _build_workspace(tmp_path)
    count = write_payloads(workspace, VERSION)
    assert count == 3

    out_dir = workspace / "qa" / "entailment-payloads"
    payload_files = sorted(p.name for p in out_dir.glob("ch-*-p*.json"))
    assert len(payload_files) == 3
    # Filenames respect the ch-NN-pNNN.json convention.
    for name in payload_files:
        assert name.startswith("ch-01-p")
        assert name.endswith(".json")

    index = json.loads((out_dir / "_index.json").read_text(encoding="utf-8"))
    assert index["version"] == VERSION
    assert len(index["payloads"]) == 3
    nodes = [r["supports_node"] for r in index["payloads"]]
    # Both fixture sub-arguments must appear at least once.
    assert "first-leg" in nodes
    assert "second-leg" in nodes


def test_payload_shape(tmp_path: Path) -> None:
    """Each payload JSON has every required field and reasonable contents."""
    workspace = _build_workspace(tmp_path)
    write_payloads(workspace, VERSION)
    out_dir = workspace / "qa" / "entailment-payloads"
    payload_paths = sorted(out_dir.glob("ch-*-p*.json"))
    assert payload_paths

    for path in payload_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert REQUIRED_FIELDS <= set(data), f"missing fields in {path.name}: {data.keys()}"
        assert data["supports_node"] in {"first-leg", "second-leg"}
        # The supports-statement comes from the compiled thesis fixture.
        assert data["supports_statement"]
        # Paragraph text is truncated and whitespace-normalised.
        assert len(data["paragraph"]) <= 600
        assert "\n" not in data["paragraph"]
        # Each node has exactly one sibling in the tiny fixture tree.
        assert isinstance(data["sibling_nodes"], list)
        assert len(data["sibling_nodes"]) <= 3
        # Expected-response label is the four-way enum string.
        assert data["expected_response"] == (
            "entailed | weakly-entailed | unrelated | contradicts")
        # Meta carries chapter + paragraph index + (possibly empty) evidence.
        assert data["meta"]["chapter"] == "ch-01"
        assert isinstance(data["meta"]["paragraph_idx"], int)
        assert data["meta"]["paragraph_idx"] >= 1

    # The paragraph that cites clm-2026-000001 picks up its canonical text.
    first_payload = next(p for p in payload_paths
                         if json.loads(p.read_text(encoding="utf-8"))["meta"]["evidence_id"]
                         == "clm-2026-000001")
    assert "First leg evidence claim." in json.loads(
        first_payload.read_text(encoding="utf-8"))["cited_claim"]
