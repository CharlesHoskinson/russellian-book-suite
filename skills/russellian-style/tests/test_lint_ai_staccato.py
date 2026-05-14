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
