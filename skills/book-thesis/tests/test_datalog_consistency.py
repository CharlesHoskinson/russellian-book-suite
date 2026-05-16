"""Tests for datalog_consistency.py.

Three round-trip cases:
  - direct contradiction (two claims, same subject, different value)
  - orphan paragraph (claim supports a node unreachable from :Thesis)
  - clean pass (well-formed thesis + non-conflicting verified claims)

Each test builds a minimal workspace under tmp_path, copies the shared thesis
TTL fixture into ``.knowledge/``, writes a custom ``claims/ledger.jsonl``, and
asserts on the resulting ``qa/datalog-defects.json``.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from datalog_consistency import run  # noqa: E402

FIXTURE_TTL = Path(__file__).parent / "fixtures" / "datalog_thesis.ttl"


def _make_workspace(tmp_path: Path, claims: list[dict]) -> Path:
    """Lay out a workspace with the shared thesis TTL and the given claim ledger.

    Thesis TTL lives at ``.knowledge/thesis-triples.ttl`` — the canonical path
    that ``compile_thesis.py`` writes to and every book-thesis script reads.
    Claims live at ``claims/ledger.jsonl`` — the canonical book-knowledge layout.
    """
    knowledge = tmp_path / ".knowledge"
    knowledge.mkdir(parents=True)
    shutil.copy(FIXTURE_TTL, knowledge / "thesis-triples.ttl")
    claims_dir = tmp_path / "claims"
    claims_dir.mkdir(parents=True)
    with (claims_dir / "ledger.jsonl").open("w", encoding="utf-8") as fh:
        for rec in claims:
            fh.write(json.dumps(rec) + "\n")
    return tmp_path


def _load_payload(workspace: Path) -> dict:
    return json.loads((workspace / "qa" / "datalog-defects.json").read_text(encoding="utf-8"))


def test_detects_direct_contradiction(tmp_path: Path) -> None:
    """Two verified claims share a subject but assert different values."""
    ws = _make_workspace(tmp_path, [
        {"claim_id": "clm-a", "status": "verified", "subject": "parish_count",
         "value": 9, "supports_nodes": ["first-leg"]},
        {"claim_id": "clm-b", "status": "verified", "subject": "parish_count",
         "value": 10, "supports_nodes": ["second-leg"]},
    ])
    report = run(ws)
    payload = _load_payload(ws)
    assert payload["summary"]["contradictions"] >= 1
    rules = {d["rule"] for d in payload["defects"] if d["class"] == "D10"}
    assert "direct_contradiction" in rules
    pair = next(d["facts"] for d in payload["defects"] if d["rule"] == "direct_contradiction")
    assert set(pair) == {"clm-a", "clm-b"}
    assert report.gate_failed()


def test_detects_orphan(tmp_path: Path) -> None:
    """Claim supports a node that exists nowhere in the thesis tree."""
    ws = _make_workspace(tmp_path, [
        {"claim_id": "clm-good", "status": "verified", "subject": "source-alpha",
         "value": "ok", "supports_nodes": ["first-leg"]},
        {"claim_id": "clm-lost", "status": "verified", "subject": "source-beta",
         "value": "ok", "supports_nodes": ["floating-leg"]},
    ])
    run(ws)
    payload = _load_payload(ws)
    orphans = [d for d in payload["defects"] if d["rule"] == "orphan_paragraph"]
    assert any("clm-lost" in d["facts"] for d in orphans)
    # The good claim should not be flagged as orphan.
    assert not any("clm-good" in d["facts"] for d in orphans)
    # Unreachable supports invariant should fire on the lost claim.
    invariants = [d for d in payload["defects"] if d["rule"] == "unreachable_supports"]
    assert any("clm-lost" in d["facts"] for d in invariants)


def test_clean_pass(tmp_path: Path) -> None:
    """Well-formed claim set + thesis tree should produce zero gate-failing defects."""
    ws = _make_workspace(tmp_path, [
        {"claim_id": "clm-x", "status": "verified", "subject": "source-alpha",
         "value": "ok", "supports_nodes": ["first-leg"], "supports_chapters": ["ch-01"]},
        {"claim_id": "clm-y", "status": "verified", "subject": "source-beta",
         "value": "ok", "supports_nodes": ["second-leg"], "supports_chapters": ["ch-02"]},
    ])
    report = run(ws)
    payload = _load_payload(ws)
    assert payload["summary"]["contradictions"] == 0
    assert payload["summary"]["invariant_violations"] == 0
    assert payload["summary"]["orphans"] == 0
    assert not report.gate_failed()
