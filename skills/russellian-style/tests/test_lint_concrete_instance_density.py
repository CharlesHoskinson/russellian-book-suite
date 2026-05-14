"""lint_concrete_instance_density: NER count per paragraph; flag 3+ consecutive paragraphs with zero."""
from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_three_abstract_paragraphs_flagged(tmp_path):
    from scripts.lint_concrete_instance_density import lint_concrete_instance_density
    text = (
        "The system processes inputs. The framework outputs results.\n\n"
        "The platform abstracts away complexity. The pipeline orchestrates stages.\n\n"
        "The architecture is layered. The implementation is modular.\n"
    )
    findings = lint_concrete_instance_density(_write(tmp_path, text))
    assert any(f["rule"] == "concrete-instance-density" for f in findings)


def test_concrete_paragraphs_pass(tmp_path):
    from scripts.lint_concrete_instance_density import lint_concrete_instance_density
    text = (
        "Russell wrote in 1912 that philosophy starts with simple things.\n\n"
        "The Royal Society convened in London on May 14th, 1660.\n\n"
        "Cambridge admitted Wittgenstein in October 1911.\n"
    )
    findings = lint_concrete_instance_density(_write(tmp_path, text))
    assert findings == []


def test_occupational_noun_counts_as_concrete(tmp_path):
    from scripts.lint_concrete_instance_density import lint_concrete_instance_density
    text = (
        "The censor approved the bulletin. The official signed the order.\n\n"
        "The philosopher disputed the claim. The worker filed a grievance.\n\n"
        "The student handed in the essay. The judge sealed the ruling.\n"
    )
    findings = lint_concrete_instance_density(_write(tmp_path, text))
    assert findings == []
