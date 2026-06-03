import pytest
pytestmark = pytest.mark.windows_canary
import json
from pathlib import Path
from scripts.aggregate_halmos import aggregate_halmos, rollup


def test_rollup_dedupes_and_counts():
    linkage = {"flags": [{"check": "orphan-reference", "severity": "critical", "concept": "bounded-polis", "detail": "x"}]}
    agent = {"spiral_coherence": "loose", "findings": [
        {"check": "orphan-reference", "severity": "critical", "prior_chapter": None, "concept": "bounded-polis", "detail": "dup"},
        {"check": "missed-recall", "severity": "important", "prior_chapter": "ch-06", "detail": "y", "fix": "recall it"},
    ], "per_prior_chapter": {}}
    merged = rollup(linkage, agent)
    assert merged["halmos_critical_count"] == 1   # the same-concept orphan-reference dedupes
    assert merged["important_count"] == 1
    assert merged["spiral_coherence"] == "loose"


def test_rollup_promotes_fix_and_severity_on_collision():
    # Deterministic flag is important; the colliding agent dup carries a fix AND a higher severity.
    linkage = {"flags": [{"check": "broken-seam", "severity": "important", "concept": "settlement-rung", "detail": "x"}]}
    agent = {"spiral_coherence": "loose", "findings": [
        {"check": "broken-seam", "severity": "critical", "prior_chapter": None, "concept": "settlement-rung",
         "detail": "dup", "fix": "stitch the seam"},
    ], "per_prior_chapter": {}}
    merged = rollup(linkage, agent)
    rec = next(f for f in merged["findings"] if f["check"] == "broken-seam")
    assert rec["fix"] == "stitch the seam"
    assert rec["severity"] == "critical"
    assert merged["halmos_critical_count"] == 1
    assert merged["important_count"] == 0


def test_rollup_collision_keeps_more_severe():
    # existing important, incoming critical -> critical
    linkage = {"flags": [{"check": "orphan-reference", "severity": "important", "concept": "polis", "detail": "x"}]}
    agent = {"findings": [
        {"check": "orphan-reference", "severity": "critical", "concept": "polis", "detail": "dup"},
    ]}
    merged = rollup(linkage, agent)
    rec = next(f for f in merged["findings"] if f["check"] == "orphan-reference")
    assert rec["severity"] == "critical"
    assert merged["halmos_critical_count"] == 1

    # reverse: existing critical, incoming minor -> stays critical
    linkage = {"flags": [{"check": "orphan-reference", "severity": "critical", "concept": "polis", "detail": "x"}]}
    agent = {"findings": [
        {"check": "orphan-reference", "severity": "minor", "concept": "polis", "detail": "dup"},
    ]}
    merged = rollup(linkage, agent)
    rec = next(f for f in merged["findings"] if f["check"] == "orphan-reference")
    assert rec["severity"] == "critical"
    assert merged["halmos_critical_count"] == 1
    assert merged["minor_count"] == 0


def test_rollup_collapses_same_detail_targetless_findings():
    # Two continuity-gaps with no concept/prior_chapter and the SAME detail collapse to one.
    agent = {"spiral_coherence": "loose", "findings": [
        {"check": "continuity-gap", "severity": "critical", "prior_chapter": None, "detail": "skips the settlement rung"},
        {"check": "continuity-gap", "severity": "critical", "prior_chapter": None, "detail": "skips the settlement rung"},
    ], "per_prior_chapter": {}}
    merged = rollup({"flags": []}, agent)
    assert len([f for f in merged["findings"] if f["check"] == "continuity-gap"]) == 1


def test_rollup_keeps_distinct_targetless_findings():
    # Two continuity-gaps with no concept and no prior_chapter must NOT collapse.
    agent = {"spiral_coherence": "loose", "findings": [
        {"check": "continuity-gap", "severity": "critical", "prior_chapter": None, "detail": "skips the settlement rung"},
        {"check": "continuity-gap", "severity": "critical", "prior_chapter": None, "detail": "assumes standing not yet built"},
    ], "per_prior_chapter": {}}
    merged = rollup({"flags": []}, agent)
    assert merged["halmos_critical_count"] == 2


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
