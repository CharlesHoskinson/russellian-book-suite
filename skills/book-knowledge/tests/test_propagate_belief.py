import math
from scripts.belief_graph import BeliefGraph, BeliefNode
from scripts.propagate_belief import propagate, COUNTER_OPEN_DAMP, COUNTER_ADDRESSED_DAMP


def _g_single(status="verified", sources=("src1",), p_prior=None):
    g = BeliefGraph()
    g.nodes["clm-x"] = BeliefNode(
        claim_id="clm-x", status=status, sources=list(sources), p_prior=p_prior,
    )
    return g


def test_single_claim_uses_prior_unchanged():
    g = _g_single(status="verified")
    trust = {"src1": 1.0}
    posts = propagate(g, trust, counter_claims=[])
    assert math.isclose(posts["clm-x"], 0.70, rel_tol=1e-6)


def test_two_independent_sources_corroborate():
    g = BeliefGraph()
    g.nodes["clm-y"] = BeliefNode(
        claim_id="clm-y", status="verified", sources=["s1", "s2"],
    )
    trust = {"s1": 1.0, "s2": 1.0}
    posts = propagate(g, trust, counter_claims=[])
    # 1 - (1-0.7)*(1-0.7) = 1 - 0.09 = 0.91
    assert math.isclose(posts["clm-y"], 0.91, rel_tol=1e-6)


def test_clamped_to_max():
    g = BeliefGraph()
    g.nodes["clm-z"] = BeliefNode(
        claim_id="clm-z", status="verified", sources=[f"s{i}" for i in range(20)],
    )
    trust = {f"s{i}": 1.0 for i in range(20)}
    posts = propagate(g, trust, counter_claims=[])
    assert posts["clm-z"] == 0.95  # clamped


def test_low_trust_source_reduces_evidence():
    g = _g_single(sources=["s1"])
    trust = {"s1": 0.5}
    posts = propagate(g, trust, counter_claims=[])
    # With trust=0.5, effective evidence = 0.7 * 0.5 = 0.35
    assert math.isclose(posts["clm-x"], 0.35, rel_tol=1e-6)


def test_open_counter_claim_damps():
    g = _g_single(status="verified", sources=["s1"])
    g.nodes["clm-x"].counter_claim_ids = ["cc-1"]
    trust = {"s1": 1.0}
    counter_claims = [{"id": "cc-1", "target_claim_id": "clm-x", "status": "open"}]
    posts = propagate(g, trust, counter_claims=counter_claims)
    assert math.isclose(posts["clm-x"], 0.70 * COUNTER_OPEN_DAMP, rel_tol=1e-6)


def test_addressed_counter_claim_damps_more_than_open():
    g_open = _g_single(); g_open.nodes["clm-x"].counter_claim_ids = ["cc-1"]
    g_addr = _g_single(); g_addr.nodes["clm-x"].counter_claim_ids = ["cc-1"]
    trust = {"src1": 1.0}
    posts_open = propagate(g_open, trust,
        counter_claims=[{"id": "cc-1", "target_claim_id": "clm-x", "status": "open"}])
    posts_addr = propagate(g_addr, trust,
        counter_claims=[{"id": "cc-1", "target_claim_id": "clm-x", "status": "addressed"}])
    assert posts_addr["clm-x"] < posts_open["clm-x"]
    assert math.isclose(posts_addr["clm-x"] / posts_open["clm-x"],
                        COUNTER_ADDRESSED_DAMP / COUNTER_OPEN_DAMP, rel_tol=1e-6)


import json
from pathlib import Path
from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.propagate_belief import write_snapshot


def test_write_snapshot_creates_iso_named_file(tmp_path):
    init_workspace(tmp_path)
    layout = WorkspaceLayout(tmp_path)
    layout.ledger.write_text(
        json.dumps({"claim_id": "clm-2026-000001", "canonical_text": "Hi.",
                    "status": "verified", "claim_type": "fact", "confidence": 0.7,
                    "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
                    "created_at": "2026-05-11T00:00:00Z"}) + "\n",
        encoding="utf-8",
    )
    path = write_snapshot(tmp_path)
    assert path.exists()
    assert path.parent == layout.root / "claims" / "snapshots"
    assert path.name.endswith(".jsonl")
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["claim_id"] == "clm-2026-000001"
