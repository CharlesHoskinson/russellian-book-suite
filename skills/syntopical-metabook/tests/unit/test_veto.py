import os
import sys
import json
from pathlib import Path
from scripts.acquire.rank_candidates import ScoredCandidate
from scripts.acquire.triage import TriageResult, TriageConfig
from scripts.acquire.veto import apply_veto

STUB = Path(__file__).resolve().parents[1] / "fixtures" / "booklogic_stub.py"

class _Tree:
    def __init__(self, chapter_id, nodes=None):
        self.chapter_id = chapter_id
        self.nodes = nodes or []

def _candidate_dict(id, score):
    """The veto needs a candidate-shaped object. The triage result holds
    ScoredCandidates; apply_veto looks them up by id in this lookup dict."""
    return {"id": id, "extracted_concepts": [], "embedding_score": score}

def test_veto_passes_when_stub_returns_reachable_true(tmp_path, monkeypatch):
    monkeypatch.setenv("BOOKLOGIC_BIN", f"{sys.executable} {STUB}")
    tr = TriageResult(run_id="r1", auto_approve=[ScoredCandidate("c1", 0.82)])
    lookup = {"c1": _candidate_dict("c1", 0.82)}
    manifest = tmp_path / "manifest.jsonl"
    apply_veto(tr, _Tree("ch-01"), lookup, manifest_path=manifest)
    # Stub returns reachable=true; candidate stays in auto-approve.
    assert [c.id for c in tr.auto_approve] == ["c1"]
    assert tr.manual_review == []
    assert not manifest.exists() or manifest.read_text() == ""

def test_veto_demotes_when_unreachable(tmp_path, monkeypatch):
    # Replace the adapter call with a one-shot mock that returns reachable=False
    from scripts.acquire import veto as veto_mod
    from scripts.booklogic_adapter import ReachabilityVerdict
    monkeypatch.setattr(veto_mod, "_reachable_from_thesis",
                        lambda cand, tree: ReachabilityVerdict(
                            candidate_id=cand.id, reachable=False,
                            rule_trace=["rule-off-thesis-1"], branch_witness=None))
    tr = TriageResult(run_id="r1", auto_approve=[ScoredCandidate("c1", 0.82)])
    lookup = {"c1": _candidate_dict("c1", 0.82)}
    apply_veto(tr, _Tree("ch-01"), lookup,
               manifest_path=tmp_path / "manifest.jsonl")
    assert tr.auto_approve == []
    assert [c.id for c in tr.manual_review] == ["c1"]
    assert "booklogic-veto" in tr.notes["c1"][0]
    assert "rule-off-thesis-1" in tr.notes["c1"][0]

def test_env_bypass_skips_veto(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTOPICAL_NO_BOOKLOGIC", "1")
    tr = TriageResult(run_id="r1", auto_approve=[ScoredCandidate("c1", 0.82)])
    lookup = {"c1": _candidate_dict("c1", 0.82)}
    manifest = tmp_path / "manifest.jsonl"
    apply_veto(tr, _Tree("ch-01"), lookup, manifest_path=manifest)
    assert tr.auto_approve and tr.auto_approve[0].id == "c1"
    assert manifest.exists()
    record = json.loads(manifest.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert record["kind"] == "booklogic-veto-skipped"
    assert record["candidate_ids"] == ["c1"]
    assert record["reason"] == "env"
