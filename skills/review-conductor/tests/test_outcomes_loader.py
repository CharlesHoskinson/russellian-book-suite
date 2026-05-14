"""Outcomes loader: load exemplar findings, pick representative samples deterministically."""
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "synthetic_outcomes" / "sample-pass-1"


def test_load_exemplars_returns_per_persona_findings():
    from scripts.outcomes_loader import load_exemplars
    exemplars = load_exemplars([FIXTURES])
    assert set(exemplars.keys()) == {"gottlieb", "lay-reader"}
    assert len(exemplars["gottlieb"]) >= 1
    assert "synthetic gottlieb critical" in exemplars["gottlieb"][0].text.lower()


def test_pick_findings_seed_stable():
    from scripts.outcomes_loader import load_exemplars, pick_findings
    exemplars = load_exemplars([FIXTURES])
    a = pick_findings(exemplars, per_persona=1, seed=42)
    b = pick_findings(exemplars, per_persona=1, seed=42)
    assert a == b


def test_pick_findings_respects_per_persona_count():
    from scripts.outcomes_loader import load_exemplars, pick_findings
    exemplars = load_exemplars([FIXTURES])
    picked = pick_findings(exemplars, per_persona=1, seed=42)
    for persona_id, findings in picked.items():
        assert len(findings) <= 1


def test_render_few_shot_returns_markdown():
    from scripts.outcomes_loader import load_exemplars, pick_findings, render_few_shot
    exemplars = load_exemplars([FIXTURES])
    picked = pick_findings(exemplars, per_persona=1, seed=42)
    md = render_few_shot("gottlieb", picked)
    assert "Recent findings" in md
    assert "synthetic gottlieb critical" in md.lower()


def test_empty_paths_returns_empty_dict():
    from scripts.outcomes_loader import load_exemplars
    assert load_exemplars([]) == {}
