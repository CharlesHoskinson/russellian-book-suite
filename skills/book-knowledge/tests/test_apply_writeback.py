import pytest

pytestmark = pytest.mark.windows_canary

import json

from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ledger import append_claim
from scripts.counter_claims import append_counter_claim, read_counter_claims
from scripts.apply_writeback import apply_writeback
from scripts.events_log import read_events


def _seed_claim(tmp_path):
    init_workspace(tmp_path)
    layout = WorkspaceLayout(tmp_path)
    append_claim(layout, {
        "claim_id": "clm-2026-000001", "canonical_text": "Hi text.",
        "status": "verified", "claim_type": "fact", "confidence": 0.7,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
    })
    return layout


def test_apply_writeback_propose_only_default(tmp_path):
    _seed_claim(tmp_path)
    (tmp_path / "claims" / "proposed-transitions.jsonl").write_text(json.dumps({
        "kind": "claim", "claim_id": "clm-2026-000001",
        "from": "verified", "to": "disputed",
        "cause_ticket_id": "tkt-1", "cause_class": "unsupported_claim",
        "severity": "critical",
    }) + "\n", encoding="utf-8")
    summary = apply_writeback(tmp_path, auto_apply=False)
    assert summary["applied"] == 0
    assert summary["proposed"] == 1
    assert read_events(tmp_path) == []


def test_apply_writeback_auto_apply_critical(tmp_path):
    _seed_claim(tmp_path)
    (tmp_path / "claims" / "proposed-transitions.jsonl").write_text(json.dumps({
        "kind": "claim", "claim_id": "clm-2026-000001",
        "from": "verified", "to": "disputed",
        "cause_ticket_id": "tkt-1", "cause_class": "unsupported_claim",
        "severity": "critical",
    }) + "\n", encoding="utf-8")
    summary = apply_writeback(tmp_path, auto_apply=True)
    assert summary["applied"] == 1
    events = read_events(tmp_path)
    assert events[-1]["to"] == "disputed"


def test_apply_writeback_skips_non_critical_in_auto(tmp_path):
    _seed_claim(tmp_path)
    (tmp_path / "claims" / "proposed-transitions.jsonl").write_text(json.dumps({
        "kind": "claim", "claim_id": "clm-2026-000001",
        "from": "verified", "to": "disputed",
        "cause_ticket_id": "tkt-1", "cause_class": "unsupported_claim",
        "severity": "important",
    }) + "\n", encoding="utf-8")
    summary = apply_writeback(tmp_path, auto_apply=True)
    assert summary["applied"] == 0


def test_apply_writeback_blocks_human_review_proposals(tmp_path):
    """REQ-QA-PIPE-012: :requires :human-review blocks auto-apply."""
    _seed_claim(tmp_path)
    (tmp_path / "claims" / "proposed-transitions.jsonl").write_text(json.dumps({
        "kind": "claim", "claim_id": "clm-2026-000001",
        "to": "refuted",
        "cause_ticket_id": "W001", "cause_class": "booklogic_remedy",
        "severity": "critical", "requires": "human-review", "auto_apply": False,
    }) + "\n", encoding="utf-8")
    summary = apply_writeback(tmp_path, auto_apply=True)
    assert summary["applied"] == 0


def test_apply_writeback_counter_claim_auto_applies(tmp_path):
    init_workspace(tmp_path)
    append_counter_claim(tmp_path, {
        "id": "cc-2026-abcdef", "target_claim_id": "clm-2026-000001",
        "text": "Rival hypothesis here.", "disagreement_vector": "scope",
        "status": "open",
        "provenance": {"generator": "abduction-v1", "prompt_sha256": "0"*64},
        "created_at": "2026-05-11T00:00:00Z", "addressed_in_chapter": None,
    })
    (tmp_path / "claims" / "proposed-transitions.jsonl").write_text(json.dumps({
        "kind": "counter_claim", "counter_claim_id": "cc-2026-abcdef",
        "new_status": "addressed", "chapter_id": "ch07",
        "cause_ticket_id": "tkt-2", "cause_class": "addressed_rival",
        "severity": "important",
    }) + "\n", encoding="utf-8")
    summary = apply_writeback(tmp_path, auto_apply=True)
    assert summary["applied"] == 1
    items = read_counter_claims(tmp_path)
    latest = [r for r in items if r["id"] == "cc-2026-abcdef"][-1]
    assert latest["status"] == "addressed"
    assert latest["addressed_in_chapter"] == "ch07"
