from pathlib import Path
from scripts.acquire.rank_candidates import ScoredCandidate
from scripts.acquire.triage import triage, TriageResult, TriageConfig

def test_partition_three_buckets(tmp_path):
    scored = [
        ScoredCandidate("hi", 0.82),
        ScoredCandidate("mid", 0.62),
        ScoredCandidate("lo", 0.41),
    ]
    cfg = TriageConfig(t_high=0.75, t_low=0.55, max_auto_per_run=25)
    res = triage(scored, cfg, workspace_root=tmp_path, run_id="r1")
    assert [c.id for c in res.auto_approve] == ["hi"]
    assert [c.id for c in res.manual_review] == ["mid"]
    assert [c.id for c in res.reject] == ["lo"]
    out = tmp_path / "syntopical" / "acquisition" / "triage-r1.md"
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "auto-approve" in body and "manual-review" in body and "reject" in body

def test_max_auto_per_run_caps_auto_bucket(tmp_path):
    scored = [ScoredCandidate(f"c{i}", 0.9) for i in range(30)]
    cfg = TriageConfig(t_high=0.75, t_low=0.55, max_auto_per_run=10)
    res = triage(scored, cfg, workspace_root=tmp_path, run_id="r2")
    assert len(res.auto_approve) == 10
    # Overflow goes to manual_review per REQ-ACQ-3
    assert len(res.manual_review) == 20
