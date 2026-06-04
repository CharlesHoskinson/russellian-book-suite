"""aggregate_panel emits verdict.json + panel-review.md and applies per-persona severity gates."""
import pytest

pytestmark = pytest.mark.windows_canary

import json
from pathlib import Path
from shutil import copytree

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "synthetic_reviews"


def _setup_workspace_with_reviews(tmp_path: Path, fixture_name: str, chapter_id: str = "ch-test") -> Path:
    workspace = tmp_path / "workspace"
    draft_dir = workspace / "chapters" / "drafts" / chapter_id
    draft_dir.mkdir(parents=True)
    (draft_dir / "draft.md").write_text("# test\n", encoding="utf-8")
    copytree(FIXTURES / fixture_name, draft_dir / "reviews")
    return workspace


def _panel(personas):
    from scripts.load_panel import Panel, PersonaConfig, VerdictConfig, OutcomesConfig, OutputConfig
    return Panel(
        panel_id="test", artifact_scope="chapter", description="",
        personas=[PersonaConfig(id=p, severity_gate=g) for p, g in personas],
        verdict=VerdictConfig(hard_gate=False, soft_gate_rule="any_critical_from_gating"),
        outcomes=OutcomesConfig(exemplar_paths=[], per_persona_exemplars=0),
        output=OutputConfig(
            panel_report_path="chapters/drafts/{chapter_id}/panel-review.md",
            verdict_path="chapters/drafts/{chapter_id}/verdict.json",
        ),
    )


def test_verdict_pass_when_all_clean(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "all-clean")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "pass"
    assert verdict["gating_criticals"] == 0
    assert verdict["advisory_criticals"] == 0


def test_verdict_soft_gate_fail_when_gating_critical(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "gating-critical")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "soft-gate-fail"
    assert verdict["gating_criticals"] == 1


def test_verdict_pass_when_only_advisory_critical(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "advisory-critical-only")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "pass"
    assert verdict["gating_criticals"] == 0
    assert verdict["advisory_criticals"] == 1


def test_verdict_json_written_to_workspace(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "gating-critical")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    verdict_path = workspace / "chapters" / "drafts" / "ch-test" / "verdict.json"
    assert verdict_path.is_file()
    on_disk = json.loads(verdict_path.read_text(encoding="utf-8"))
    assert on_disk["verdict"] == verdict["verdict"]


def test_panel_review_md_written(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "gating-critical")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    run_aggregation(workspace, "ch-test", panel)
    report = workspace / "chapters" / "drafts" / "ch-test" / "panel-review.md"
    assert report.is_file()
    text = report.read_text(encoding="utf-8")
    assert "synthetic gottlieb critical" in text.lower()


def _write_review(workspace: Path, chapter_id: str, filename: str, body: str) -> None:
    reviews = workspace / "chapters" / "drafts" / chapter_id / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / filename).write_text(body, encoding="utf-8")


_CLEAN_REPORT = """---
persona: {persona}
chapter_id: synth-ch
verdict: APPROVED
critical_count: 0
important_count: 0
minor_count: 0
reviewed_at: 2026-05-13T00:00:00Z
---

## Critical findings
- _(none)_

## Important findings
- _(none)_

## Minor findings
- _(none)_
"""


def _make_bare_workspace(tmp_path: Path, chapter_id: str = "ch-test") -> Path:
    workspace = tmp_path / "workspace"
    draft_dir = workspace / "chapters" / "drafts" / chapter_id
    draft_dir.mkdir(parents=True)
    (draft_dir / "draft.md").write_text("# test\n", encoding="utf-8")
    return workspace


def test_missing_gating_report_fails_closed(tmp_path):
    """A configured gating persona that produced no report must not pass."""
    from scripts.aggregate_panel import run_aggregation
    workspace = _make_bare_workspace(tmp_path)
    # Only the advisory persona reported; the gating persona's subagent crashed.
    _write_review(workspace, "ch-test", "lay-reader.md", _CLEAN_REPORT.format(persona="lay-reader"))
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "hard-gate-fail"


def test_unparseable_gating_report_fails_closed(tmp_path):
    """A gating persona whose report fails to parse must not pass."""
    from scripts.aggregate_panel import run_aggregation
    workspace = _make_bare_workspace(tmp_path)
    _write_review(workspace, "ch-test", "lay-reader.md", _CLEAN_REPORT.format(persona="lay-reader"))
    # gottlieb's report has no frontmatter -> parse_review_report raises ValueError.
    _write_review(workspace, "ch-test", "gottlieb.md", "garbage with no frontmatter\n")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "hard-gate-fail"


def test_unrecognized_persona_id_not_silently_advisory(tmp_path):
    """A report whose persona id matches no configured persona must not be
    silently downgraded to advisory and dropped from the gate."""
    from scripts.aggregate_panel import run_aggregation
    workspace = _make_bare_workspace(tmp_path)
    # Both configured personas report cleanly...
    _write_review(workspace, "ch-test", "gottlieb.md", _CLEAN_REPORT.format(persona="gottlieb"))
    _write_review(workspace, "ch-test", "lay-reader.md", _CLEAN_REPORT.format(persona="lay-reader"))
    # ...but a stray report carries a stale/typo'd persona id with a critical.
    stray = _CLEAN_REPORT.replace("critical_count: 0", "critical_count: 1").replace(
        "## Critical findings\n- _(none)_",
        "## Critical findings\n1. **[line 1]:** stray critical from a mistyped persona id.",
    ).format(persona="gotlieb")  # typo
    _write_review(workspace, "ch-test", "gotlieb.md", stray)
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "hard-gate-fail"


def test_advisory_report_missing_still_passes(tmp_path):
    """An absent advisory persona does not block: only gating completeness gates."""
    from scripts.aggregate_panel import run_aggregation
    workspace = _make_bare_workspace(tmp_path)
    _write_review(workspace, "ch-test", "gottlieb.md", _CLEAN_REPORT.format(persona="gottlieb"))
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "pass"


def _panel_rule(personas, rule):
    from scripts.load_panel import Panel, PersonaConfig, VerdictConfig, OutcomesConfig, OutputConfig
    return Panel(
        panel_id="test", artifact_scope="chapter", description="",
        personas=[PersonaConfig(id=p, severity_gate=g) for p, g in personas],
        verdict=VerdictConfig(hard_gate=False, soft_gate_rule=rule),
        outcomes=OutcomesConfig(exemplar_paths=[], per_persona_exemplars=0),
        output=OutputConfig(
            panel_report_path="chapters/drafts/{chapter_id}/panel-review.md",
            verdict_path="chapters/drafts/{chapter_id}/verdict.json",
        ),
    )


_CRIT_REPORT = """---
persona: {persona}
chapter_id: synth-ch
verdict: NEEDS_WORK
critical_count: 1
important_count: 0
minor_count: 0
reviewed_at: 2026-05-13T00:00:00Z
---

## Critical findings
1. **[line 1]:** critical from {persona}.

## Important findings
- _(none)_

## Minor findings
- _(none)_
"""


def test_majority_critical_ignores_advisory_personas(tmp_path):
    """majority_critical must count/divide over gating personas only; an
    advisory persona's critical neither triggers the gate nor inflates the
    denominator."""
    from scripts.aggregate_panel import run_aggregation
    workspace = _make_bare_workspace(tmp_path)
    # Two gating personas both clean; one advisory persona flags a critical.
    _write_review(workspace, "ch-test", "a.md", _CLEAN_REPORT.format(persona="a"))
    _write_review(workspace, "ch-test", "b.md", _CLEAN_REPORT.format(persona="b"))
    _write_review(workspace, "ch-test", "c.md", _CRIT_REPORT.format(persona="c"))
    panel = _panel_rule(
        [("a", "gating"), ("b", "gating"), ("c", "advisory")], "majority_critical"
    )
    verdict = run_aggregation(workspace, "ch-test", panel)
    # No gating persona flagged a critical -> pass; advisory critical does not gate.
    assert verdict["verdict"] == "pass"


def test_majority_critical_tie_fails_closed(tmp_path):
    """An exact half-and-half split of gating personas does not pass."""
    from scripts.aggregate_panel import run_aggregation
    workspace = _make_bare_workspace(tmp_path)
    _write_review(workspace, "ch-test", "a.md", _CRIT_REPORT.format(persona="a"))
    _write_review(workspace, "ch-test", "b.md", _CRIT_REPORT.format(persona="b"))
    _write_review(workspace, "ch-test", "c.md", _CLEAN_REPORT.format(persona="c"))
    _write_review(workspace, "ch-test", "d.md", _CLEAN_REPORT.format(persona="d"))
    panel = _panel_rule(
        [("a", "gating"), ("b", "gating"), ("c", "gating"), ("d", "gating")],
        "majority_critical",
    )
    verdict = run_aggregation(workspace, "ch-test", panel)
    # 2 of 4 gating personas flag a critical -> tie -> soft-gate-fail.
    assert verdict["verdict"] == "soft-gate-fail"


def test_majority_critical_majority_fails(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _make_bare_workspace(tmp_path)
    _write_review(workspace, "ch-test", "a.md", _CRIT_REPORT.format(persona="a"))
    _write_review(workspace, "ch-test", "b.md", _CRIT_REPORT.format(persona="b"))
    _write_review(workspace, "ch-test", "c.md", _CLEAN_REPORT.format(persona="c"))
    panel = _panel_rule(
        [("a", "gating"), ("b", "gating"), ("c", "gating")], "majority_critical"
    )
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "soft-gate-fail"
