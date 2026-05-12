"""End-to-end: plant a bad claim, propose+apply writeback, verify progression."""
import json
import math
from pathlib import Path

from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ledger import append_claim, read_claims
from scripts.apply_writeback import apply_writeback
from scripts.events_log import read_events
from scripts.belief_graph import load_belief_graph
from scripts.propagate_belief import run as propagate_run


def _write_proposed(workspace_root: Path, transition: dict) -> None:
    p = workspace_root / "claims" / "proposed-transitions.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(transition) + "\n", encoding="utf-8")


def test_bad_claim_progression(tmp_path):
    init_workspace(tmp_path)
    layout = WorkspaceLayout(tmp_path)

    append_claim(layout, {
        "claim_id": "clm-2026-000001",
        "canonical_text": "A claim that the QA will later find unsupported.",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.8,
        "source_spans": [{"doc_id": "d", "locator_text": "ZZZZ"}],
        "supports_chapters": ["ch01"],
        "load_bearing": True,
        "created_at": "2026-05-11T00:00:00Z",
    })

    # ----- Round 1: unsupported_claim → verified → disputed (auto-applied)
    _write_proposed(tmp_path, {
        "kind": "claim",
        "claim_id": "clm-2026-000001",
        "from": "verified",
        "to": "disputed",
        "cause_ticket_id": "ch01-D11-01",
        "cause_class": "unsupported_claim",
        "severity": "critical",
    })
    s1 = apply_writeback(tmp_path, auto_apply=True)
    assert s1["applied"] == 1

    bg = load_belief_graph(tmp_path)
    assert bg.nodes["clm-2026-000001"].status == "disputed"

    events = read_events(tmp_path)
    assert len(events) == 1
    assert events[0]["from"] == "verified"
    assert events[0]["to"] == "disputed"

    records = read_claims(layout)
    latest = [r for r in records if r["claim_id"] == "clm-2026-000001"][-1]
    assert latest["p_prior"] == 0.2  # prior_for_status("disputed")

    # ----- Round 2: refuted_by_new_source is NOT in the auto-apply whitelist
    _write_proposed(tmp_path, {
        "kind": "claim",
        "claim_id": "clm-2026-000001",
        "from": "disputed",
        "to": "refuted",
        "cause_ticket_id": "ch01-D11-02",
        "cause_class": "refuted_by_new_source",
        "severity": "critical",
    })
    s2 = apply_writeback(tmp_path, auto_apply=True)
    assert s2["applied"] == 0  # gated by policy: cause_class not "unsupported_claim"

    # Operator forces the transition (simulating manual approval).
    from scripts.ledger import transition_status
    transition_status(
        layout, "clm-2026-000001", "refuted",
        cause_ticket_id="ch01-D11-02",
        cause_class="refuted_by_new_source",
        operator="operator@manual",
    )

    bg = load_belief_graph(tmp_path)
    assert bg.nodes["clm-2026-000001"].status == "refuted"

    events = read_events(tmp_path)
    assert len(events) == 2
    assert events[-1]["to"] == "refuted"

    records = read_claims(layout)
    latest = [r for r in records if r["claim_id"] == "clm-2026-000001"][-1]
    assert latest["p_prior"] == 0.05  # prior_for_status("refuted")

    # ----- Belief propagation clamps refuted claim's posterior at the floor.
    propagate_run(tmp_path, run_id="integration-test")

    # Re-read: propagate_run appends a new record with p_posterior set.
    records = read_claims(layout)
    latest = [r for r in records if r["claim_id"] == "clm-2026-000001"][-1]
    assert "p_posterior" in latest
    # Effective evidence = 0.05 * 1.0 (one source, trust 1.0) → ~0.05,
    # clamped to floor [0.05, 0.95] → 0.05.  Use isclose for float safety.
    assert math.isclose(latest["p_posterior"], 0.05, rel_tol=1e-6)
