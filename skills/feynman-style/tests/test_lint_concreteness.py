import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_concreteness import lint_concreteness


def test_flags_abstraction_heavy(tmp_path):
    md = tmp_path / "abstract.md"
    md.write_text(
        "The implementation of the abstraction enables the realization of the "
        "generalization through the formalization of the representation and the "
        "specification of the configuration.\n",
        encoding="utf-8",
    )
    rules = {f["rule"] for f in lint_concreteness(md)}
    assert "abstraction-heavy" in rules

def test_flags_missing_analogy(tmp_path):
    md = tmp_path / "noanalogy.md"
    md.write_text(
        "The electron moves through the field and changes its momentum. "
        "The field exerts a force. The force acts over a distance. "
        "Energy transfers from the field to the particle in measurable amounts.\n",
        encoding="utf-8",
    )
    rules = {f["rule"] for f in lint_concreteness(md)}
    assert "analogy-absent" in rules

def test_concrete_analogy_passes(tmp_path):
    md = tmp_path / "concrete.md"
    md.write_text(
        "Think of the electron like a marble rolling down a hill. "
        "The steeper the hill, the faster it picks up speed, just like a ball on a ramp.\n",
        encoding="utf-8",
    )
    assert lint_concreteness(md) == []


def test_predicate_metaphor_counts_as_analogy(tmp_path):
    # Regression: a metaphor with no simile keyword ("wearing a tie") is an analogy.
    md = tmp_path / "metaphor.md"
    md.write_text(
        "The gap between the two scores is tiny, far smaller than the wobble between runs, "
        "so calling it an improvement is really just noise wearing a tie and pretending to be signal.\n",
        encoding="utf-8",
    )
    assert not any(f["rule"] == "analogy-absent" for f in lint_concreteness(md))
