"""lint_paragraph_motion: per-paragraph shape rubric + flat-axiom-stack detection."""
import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_assertion_only_paragraphs_flagged(tmp_path):
    from scripts.lint_paragraph_motion import lint_paragraph_motion
    text = (
        "The ledger records claims.\n\n"
        "The graph projects relations.\n\n"
        "The validator enforces shapes.\n\n"
        "The report summarises findings.\n"
    )
    findings = lint_paragraph_motion(_write(tmp_path, text))
    assert any(f["rule"] == "paragraph-motion" for f in findings)
    f = [f for f in findings if f["rule"] == "paragraph-motion"][0]
    assert f["flat_proportion"] >= 0.7


def test_concession_turn_recognised():
    from scripts.lint_paragraph_motion import classify_paragraph
    para = (
        "The defender of the practice will say that the system is necessary. "
        "But the same defender, pressed on the cost, can find no answer that the "
        "tired worker will accept. The necessity, once it meets the worker, breaks."
    )
    assert classify_paragraph(para) == "concession_turn"


def test_question_answer_recognised():
    from scripts.lint_paragraph_motion import classify_paragraph
    para = (
        "What does the ledger record? It records the propositions, their sources, "
        "their state, and the transitions between states."
    )
    assert classify_paragraph(para) == "question_answer"


def test_mixed_section_not_flagged(tmp_path):
    from scripts.lint_paragraph_motion import lint_paragraph_motion
    text = (
        "What does the ledger do? It binds every claim to its source.\n\n"
        "The defender of mood will say that prose can carry truth without "
        "address. But mood, pressed by a domain reader, dissolves.\n\n"
        "Consider the auditor. She opens the ledger; therefore the ledger answers.\n\n"
        "The contract for chapter four therefore lists six claims.\n"
    )
    findings = lint_paragraph_motion(_write(tmp_path, text))
    flat = [f for f in findings if f["rule"] == "paragraph-motion"]
    assert flat == []
