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


def test_write_posteriors_appends_records(tmp_path):
    from scripts.propagate_belief import write_posteriors
    init_workspace(tmp_path)
    layout = WorkspaceLayout(tmp_path)
    base = {"claim_id": "clm-2026-000001", "canonical_text": "Hi text.",
            "status": "verified", "claim_type": "fact", "confidence": 0.7,
            "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
            "created_at": "2026-05-11T00:00:00Z"}
    layout.ledger.write_text(json.dumps(base) + "\n", encoding="utf-8")
    write_posteriors(tmp_path, {"clm-2026-000001": 0.82}, generated_by_run="run-x")
    records = [json.loads(l) for l in layout.ledger.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    assert records[1]["claim_id"] == "clm-2026-000001"
    assert records[1]["p_posterior"] == 0.82
    assert records[1]["p_prior"] == 0.7  # carried from prior_for_status("verified")
    assert records[1]["generated_by_run"] == "run-x"


def test_run_entrypoint_writes_report_and_snapshot(tmp_path):
    from scripts.propagate_belief import run
    init_workspace(tmp_path)
    layout = WorkspaceLayout(tmp_path)
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Hi text.",
        "status": "verified", "claim_type": "fact", "confidence": 0.7,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z"}) + "\n", encoding="utf-8")
    run_id = run(tmp_path, run_id="run-2026-05-11-01")
    report = layout.root / "graph" / "reports" / f"belief-propagation-{run_id}.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "clm-2026-000001" in text
    assert "histogram" in text.lower()
    snapshots = list((layout.root / "claims" / "snapshots").glob("*.jsonl"))
    assert len(snapshots) == 1


def test_run_dedupes_counter_claim_records_to_latest(tmp_path):
    """A counter-claim that has both 'open' and 'addressed' records (after promotion)
    must damp only once, using the latest status. Without dedup the damping
    compounds and pushes posteriors below the floor incorrectly."""
    from scripts.propagate_belief import run
    from scripts.workspace import init_workspace, WorkspaceLayout
    layout = init_workspace(tmp_path)
    layout = WorkspaceLayout(tmp_path)
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Load-bearing claim.",
        "status": "verified", "claim_type": "fact", "confidence": 0.8,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "supports_chapters": ["ch01"],
        "load_bearing": True,
        "counter_claim_ids": ["cc-2026-aaaaaa"],
        "created_at": "2026-05-11T00:00:00Z"}) + "\n", encoding="utf-8")
    # Counter-claim appended twice: first open, then addressed (the post-promotion state).
    cc_path = layout.root / "claims" / "counter-claims.jsonl"
    cc_path.parent.mkdir(parents=True, exist_ok=True)
    cc_path.write_text(
        json.dumps({
            "id": "cc-2026-aaaaaa", "target_claim_id": "clm-2026-000001",
            "text": "Open rival hypothesis stated here.", "disagreement_vector": "scope",
            "status": "open",
            "provenance": {"generator": "abduction-v1", "prompt_sha256": "0"*64},
            "created_at": "2026-05-11T00:00:00Z", "addressed_in_chapter": None,
        }) + "\n" +
        json.dumps({
            "id": "cc-2026-aaaaaa", "target_claim_id": "clm-2026-000001",
            "text": "Open rival hypothesis stated here.", "disagreement_vector": "scope",
            "status": "addressed",
            "provenance": {"generator": "abduction-v1", "prompt_sha256": "0"*64},
            "created_at": "2026-05-11T00:00:00Z", "addressed_in_chapter": "ch01",
        }) + "\n",
        encoding="utf-8",
    )
    run(tmp_path, run_id="dedup-test")
    # Latest record per claim_id in ledger carries the posterior.
    records = [json.loads(l) for l in layout.ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    latest = [r for r in records if r["claim_id"] == "clm-2026-000001"][-1]
    # With dedup: posterior = 0.7 * 0.85 (addressed) = 0.595
    # Without dedup (buggy): posterior = 0.7 * 0.95 * 0.85 = 0.565
    assert math.isclose(latest["p_posterior"], 0.7 * COUNTER_ADDRESSED_DAMP, rel_tol=1e-6)
