import pytest
pytestmark = pytest.mark.windows_canary
import json
from pathlib import Path
from scripts.aggregate_halmos import aggregate_halmos, rollup


def test_rollup_dedupes_and_counts():
    linkage = {"flags": [{"check": "forward-reference", "severity": "critical", "concept": "bounded-polis", "detail": "x"}]}
    agent = {"spiral_coherence": "loose", "findings": [
        {"check": "forward-reference", "severity": "critical", "prior_chapter": None, "concept": "bounded-polis", "detail": "dup"},
        {"check": "missed-recall", "severity": "important", "prior_chapter": "ch-06", "detail": "y", "fix": "recall it"},
    ], "per_prior_chapter": {}}
    merged = rollup(linkage, agent)
    assert merged["halmos_critical_count"] == 1
    assert merged["important_count"] == 1
    assert merged["spiral_coherence"] == "loose"


def test_aggregate_writes_verdict_and_report(tmp_path):
    ws = tmp_path / "ws"
    (ws / "chapters" / "drafts" / "ch-09").mkdir(parents=True)
    (ws / "chapters" / "drafts" / "ch-09" / "draft.md").write_text("# C9\n", encoding="utf-8")
    linkage = {"chapter_id": "ch-09", "flags": [], "seam": {"status": "clean", "overlap": ["x"]}}
    agent = {"spiral_coherence": "tight", "findings": [], "per_prior_chapter": {"ch-08": "clean handoff"}}
    out = aggregate_halmos(ws, "ch-09", agent, linkage)
    v = json.loads((ws / "chapters" / "drafts" / "ch-09" / "halmos-verdict.json").read_text(encoding="utf-8"))
    assert v["halmos_critical_count"] == 0 and v["reviews_complete"] is True
    assert (ws / "chapters" / "drafts" / "ch-09" / "halmos-review.md").exists()
