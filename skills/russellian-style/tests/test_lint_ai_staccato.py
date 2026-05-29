"""lint_ai_staccato: cross-paragraph staccato detection."""
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ai_staccato"


def test_staccato_paragraph_run_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "staccato_run.md")
    runs = [f for f in findings if f["rule"] == "staccato-paragraph-run"]
    assert runs, "expected staccato-paragraph-run to fire"
    f = runs[0]
    assert f["tier"] == "important"
    assert f["severity"] == "advisory"
    assert f["run_length"] >= 3


def test_staccato_paragraph_run_silent_on_varied_prose():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "staccato_run_clean.md")
    runs = [f for f in findings if f["rule"] == "staccato-paragraph-run"]
    assert runs == []


def test_negation_affirmation_template_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "negation_affirmation.md")
    hits = [f for f in findings if f["rule"] == "negation-affirmation-template"]
    assert hits, "expected negation-affirmation-template to fire"
    assert hits[0]["match_count"] >= 2


def test_negation_affirmation_template_silent_on_clean():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "negation_affirmation_clean.md")
    hits = [f for f in findings if f["rule"] == "negation-affirmation-template"]
    assert hits == []


def test_this_is_conclusion_overuse_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "this_is_stacking.md")
    hits = [f for f in findings if f["rule"] == "this-is-conclusion-overuse"]
    assert hits, "expected this-is-conclusion-overuse to fire"
    assert hits[0]["match_count"] >= 3


def test_this_is_conclusion_overuse_silent_on_clean():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "this_is_stacking_clean.md")
    hits = [f for f in findings if f["rule"] == "this-is-conclusion-overuse"]
    assert hits == []


def test_abstract_subject_run_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "abstract_subject_run.md")
    hits = [f for f in findings if f["rule"] == "abstract-subject-run"]
    assert hits, "expected abstract-subject-run to fire"
    assert hits[0]["subject"] in {"system", "protocol", "ledger"}
    assert hits[0]["run_length"] >= 4


def test_abstract_subject_run_silent_on_varied_subjects():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "abstract_subject_run_clean.md")
    hits = [f for f in findings if f["rule"] == "abstract-subject-run"]
    assert hits == []


def test_abstract_subject_run_spans_paragraph_break(tmp_path):
    # A same-subject run that crosses a blank line must be detected; the old
    # per-paragraph reset would split it into two short sub-runs and miss it.
    from scripts.lint_ai_staccato import lint_ai_staccato
    text = (
        "The system records claims as data. The system projects them onto a graph.\n\n"
        "The system validates the graph. The system blocks the release on failure.\n"
    )
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    findings = lint_ai_staccato(p)
    hits = [f for f in findings if f["rule"] == "abstract-subject-run"]
    assert hits, findings
    assert hits[0]["subject"] == "system"
    assert hits[0]["run_length"] >= 4


def test_abstract_subject_run_reports_run_start_line(tmp_path):
    # The run begins on source line 5, after two unrelated lead-in lines. The
    # reported line must be where the run started, not the paragraph's line 3.
    from scripts.lint_ai_staccato import lint_ai_staccato
    text = (
        "# Heading\n"
        "\n"
        "A reader opens the chapter and skims.\n"
        "The author replies to the reader directly.\n"
        "The system records claims. The system projects them. "
        "The system validates them. The system blocks the release.\n"
    )
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    findings = lint_ai_staccato(p)
    hits = [f for f in findings if f["rule"] == "abstract-subject-run"]
    assert hits, findings
    assert hits[0]["line"] == 5, hits[0]
