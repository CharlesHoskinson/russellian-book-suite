import pytest

pytestmark = pytest.mark.windows_canary

import json
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
    propose_writeback(ws, version="v5")
    proposed_lines = (ws / "qa" / "proposed-transitions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(proposed_lines) == 2
    md = (ws / "qa" / "ledger-writeback-v5.md").read_text(encoding="utf-8")
    assert "clm-2026-000001" in md
    assert "cc-2026-abcdef" in md


def test_missing_files_gracefully_returns_zero(tmp_path):
    ws = tmp_path / "ws"
    (ws / "qa").mkdir(parents=True)
    (ws / "claims").mkdir(parents=True)
    # No findings files written.
    propose_writeback(ws, version="v5")
    proposed = (ws / "qa" / "proposed-transitions.jsonl").read_text(encoding="utf-8").splitlines()
    assert proposed == []


def test_writeback_includes_booklogic_remedy_proposal(tmp_path):
    """REQ-QA-PIPE-010/011: propose_writeback merges BookLogic remedy proposals.

    When a workspace ships rules/remedies.edn (BookLogic source) AND a
    verdict.edn with an unsat core, propose_writeback emits the remedy's
    transition alongside the regular tickets-driven transitions.
    """
    ws = tmp_path / "ws"
    (ws / "qa").mkdir(parents=True)
    (ws / "claims").mkdir(parents=True)
    (ws / "rules").mkdir(parents=True)
    (ws / "verifier-work").mkdir(parents=True)
    # Regular ticket-shape input
    (ws / "qa" / "lint-findings.json").write_text(json.dumps({"tickets": [
        {"id": "ch07-D11-04", "class": "unsupported_claim",
         "claim_id": "clm-2026-000001", "claim_current_status": "verified",
         "severity": "critical"}
    ]}), encoding="utf-8")
    # BookLogic remedies + a verdict the remedy will match against
    (ws / "rules" / "remedies.edn").write_text(
        '{:version 1 :remedies '
        '[{:id "W001" :when (unsat-core ?claim) '
        ' :propose (ledger/transition ?claim :refuted) '
        ' :requires :human-review}]}',
        encoding="utf-8",
    )
    (ws / "verifier-work" / "verdict.edn").write_text(
        '{:version 1 :verdict :unsat '
        ':core ["clm-2026-000008"] '
        ':explanation "x" :verified-count 1}',
        encoding="utf-8",
    )
    propose_writeback(ws, version="v5")
    proposed_lines = (ws / "qa" / "proposed-transitions.jsonl").read_text(encoding="utf-8").splitlines()
    # 1 from the ticket, 1 from the remedy
    assert len(proposed_lines) == 2
    by_target = {json.loads(line).get("claim_id"): json.loads(line) for line in proposed_lines}
    # Ticket-driven transition
    assert "clm-2026-000001" in by_target
    # Remedy-driven transition
    assert "clm-2026-000008" in by_target
    remedy_proposal = by_target["clm-2026-000008"]
    assert remedy_proposal["to"] == "refuted"
    assert remedy_proposal["requires"] == "human-review"
    assert remedy_proposal["auto_apply"] is False


def test_writeback_no_remedies_file_is_inert(tmp_path):
    """REQ-QA-PIPE-010: A workspace without rules/remedies.edn behaves like pre-PR-4."""
    ws = tmp_path / "ws"
    (ws / "qa").mkdir(parents=True)
    (ws / "claims").mkdir(parents=True)
    (ws / "qa" / "lint-findings.json").write_text(json.dumps({"tickets": [
        {"id": "ch07-D11-04", "class": "unsupported_claim",
         "claim_id": "clm-2026-000001", "claim_current_status": "verified",
         "severity": "critical"}
    ]}), encoding="utf-8")
    propose_writeback(ws, version="v5")
    proposed_lines = (ws / "qa" / "proposed-transitions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(proposed_lines) == 1
