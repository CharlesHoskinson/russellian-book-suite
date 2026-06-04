"""lint_concrete_instance_density: NER count per paragraph; flag 3+ consecutive paragraphs with zero."""
import pytest

pytestmark = pytest.mark.windows_canary

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


def test_multiple_distinct_dead_zones_each_flagged(tmp_path):
    # Two separate 3-paragraph zero-instance runs, split by a concrete
    # paragraph. Both runs must be reported, not just the first.
    from scripts.lint_concrete_instance_density import lint_concrete_instance_density
    text = (
        "The system processes inputs. The framework outputs results.\n\n"
        "The platform abstracts complexity. The pipeline orchestrates stages.\n\n"
        "The architecture is layered. The implementation is modular.\n\n"
        "Russell wrote in 1912 about Cambridge and the Royal Society in London.\n\n"
        "The approach generalises the model. The process repeats the loop.\n\n"
        "The structure nests the layers. The protocol defines the handshake.\n\n"
        "The mechanism triggers the cascade. The procedure runs the routine.\n"
    )
    findings = lint_concrete_instance_density(_write(tmp_path, text))
    runs = [f for f in findings if "run_start_paragraph" in f]
    assert len(runs) == 2, f"expected two distinct runs, got {runs}"
    starts = {f["run_start_paragraph"] for f in runs}
    assert starts == {0, 4}


def test_concrete_paragraphs_pass(tmp_path):
    from scripts.lint_concrete_instance_density import lint_concrete_instance_density
    text = (
        "Russell wrote in 1912 that philosophy starts with simple things.\n\n"
        "The Royal Society convened in London on May 14th, 1660.\n\n"
        "Cambridge admitted Wittgenstein in October 1911.\n"
    )
    findings = lint_concrete_instance_density(_write(tmp_path, text))
    assert findings == []


def test_headings_and_code_not_counted_as_zero_concrete(tmp_path):
    # Two concrete paragraphs separated by headings and a fenced code block.
    # Headings/code must NOT count as zero-concrete paragraphs, so no
    # 3-consecutive-zero run exists and nothing should fire.
    from scripts.lint_concrete_instance_density import lint_concrete_instance_density
    text = (
        "Russell wrote in 1912 about Cambridge.\n\n"
        "# Section heading\n\n"
        "```\nthe system processes the framework abstractly\n```\n\n"
        "## Another heading\n\n"
        "The Royal Society convened in London in 1660.\n"
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
