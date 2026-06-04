from pathlib import Path

from scripts.health_check import HealthCheckResult
from scripts.report import render_health_check_md, render_summary_md, render_readme_md


def test_render_health_check_md_emits_table():
    results = [
        HealthCheckResult(name="pytest_suite", status="PASS", evidence="84 passed in 12.31s"),
        HealthCheckResult(name="api_smoke", status="PASS", evidence="3 fixtures OK"),
        HealthCheckResult(name="composes_with", status="WARN", evidence="book-compose=WARN(venv missing)"),
    ]
    md = render_health_check_md(results)
    assert "# Health check" in md
    assert "| Check | Status | Evidence |" in md
    assert "| pytest_suite | PASS |" in md
    assert "| composes_with | WARN |" in md


def test_render_summary_md_emits_per_mode_table():
    per_mode = [
        {"mode": "technical-exposition", "gating": 1, "advisory": 4, "verdict": "PASS"},
        {"mode": "narrative-editorial", "gating": 3, "advisory": 7, "verdict": "WARN"},
        {"mode": "polemic", "gating": 0, "advisory": 2, "verdict": "PASS"},
    ]
    md = render_summary_md(per_mode)
    assert "| Mode | Gating | Advisory | Verdict |" in md
    assert "| technical-exposition | 1 | 4 | PASS |" in md
    assert "| polemic | 0 | 2 | PASS |" in md


def test_render_readme_md_combines_verdicts():
    md = render_readme_md(
        health_verdict="PASS",
        expansion_verdict="PASS (appended 47 new entries to russellian-style index)",
        samples_verdict="PASS (3/3 modes returned PASS verdict)",
        batch_id="2026-05-21-001",
    )
    assert "# russellian-style audit" in md
    assert "PASS" in md
    assert "2026-05-21-001" in md
    assert "health-check.md" in md
    assert "expansion.md" in md
    assert "samples/summary.md" in md
