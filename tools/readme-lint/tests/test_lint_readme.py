from pathlib import Path

from scripts.lint_readme import (
    SectionLintResult,
    lint_section,
    parse_readme,
    run_full_lint,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_readme_splits_at_h2_boundaries():
    sample = (
        "# Top heading\n\n"
        "intro text\n\n"
        "## Section A\n\n"
        "<!-- voice: technical-exposition -->\n\n"
        "body A\n\n"
        "## Section B\n\n"
        "<!-- voice: narrative-editorial -->\n"
        "<!-- lint-disable: rhythm-uniform-length reason=intentional -->\n\n"
        "body B\n"
    )
    sections = parse_readme(sample)
    assert len(sections) == 2
    assert sections[0].heading == "Section A"
    assert sections[0].voice == "technical-exposition"
    assert sections[0].ignore == set()
    assert sections[1].heading == "Section B"
    assert sections[1].voice == "narrative-editorial"
    assert sections[1].ignore == {"rhythm-uniform-length"}


def test_parse_readme_missing_voice_raises():
    import pytest
    sample = "## No voice\n\nbody only\n"
    with pytest.raises(ValueError, match="No voice"):
        parse_readme(sample)


def test_lint_section_pass_fixture():
    text = (FIXTURES / "pass.md").read_text(encoding="utf-8")
    sections = parse_readme(text)
    result = lint_section(sections[0])
    assert isinstance(result, SectionLintResult)
    assert result.gating_count <= 2
    assert result.passes is True


def test_lint_section_over_threshold_fixture():
    text = (FIXTURES / "over_threshold.md").read_text(encoding="utf-8")
    sections = parse_readme(text)
    result = lint_section(sections[0])
    assert result.gating_count > 2
    assert result.passes is False


def test_lint_section_with_ignore_filters_named_rule():
    text = (FIXTURES / "with_ignore.md").read_text(encoding="utf-8")
    sections = parse_readme(text)
    result = lint_section(sections[0])
    # no-hedging is ignored; the only remaining gating issue (if any) should be other rules
    no_hedging_issues = [i for i in result.issues if i.linter == "no-hedging"]
    assert no_hedging_issues == []


def test_run_full_lint_returns_per_section_results(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text(
        (FIXTURES / "pass.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    results, exit_code = run_full_lint(readme)
    assert len(results) == 1
    assert exit_code == 0
