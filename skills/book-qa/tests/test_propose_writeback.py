import json
from pathlib import Path
from scripts.propose_writeback import propose_writeback


def test_writes_proposed_transitions_and_md(tmp_path):
    ws = tmp_path / "ws"
    (ws / "qa").mkdir(parents=True)
    (ws / "claims").mkdir(parents=True)
    (ws / "qa" / "lint-findings.json").write_text(json.dumps({"tickets": [
        {"id": "ch07-D11-04", "class": "unsupported_claim",
         "claim_id": "clm-2026-000001", "claim_current_status": "verified",
         "severity": "critical"}
    ]}), encoding="utf-8")
    (ws / "qa" / "swarm-findings.json").write_text(json.dumps({"tickets": [
        {"id": "ch07-C12-02", "class": "addressed_rival",
         "counter_claim_id": "cc-2026-abcdef", "chapter_id": "ch07",
         "severity": "important"}
    ]}), encoding="utf-8")
    out = propose_writeback(ws, version="v5")
    proposed_lines = (ws / "claims" / "proposed-transitions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(proposed_lines) == 2
    md = (ws / "qa" / "ledger-writeback-v5.md").read_text(encoding="utf-8")
    assert "clm-2026-000001" in md
    assert "cc-2026-abcdef" in md


def test_missing_files_gracefully_returns_zero(tmp_path):
    ws = tmp_path / "ws"
    (ws / "qa").mkdir(parents=True)
    (ws / "claims").mkdir(parents=True)
    # No findings files written.
    out = propose_writeback(ws, version="v5")
    proposed = (ws / "claims" / "proposed-transitions.jsonl").read_text(encoding="utf-8").splitlines()
    assert proposed == []
