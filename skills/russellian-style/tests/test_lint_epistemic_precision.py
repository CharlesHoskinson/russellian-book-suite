"""lint_epistemic_precision: banned vague / allowed bounded / required uncertainty."""
from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_banned_vague_flagged(tmp_path):
    from scripts.lint_epistemic_precision import lint_epistemic_precision
    text = "Perhaps the system fails. It could be argued that the design is flawed."
    findings = lint_epistemic_precision(_write(tmp_path, text))
    cats = {f["category"] for f in findings}
    assert "banned_vague" in cats


def test_allowed_bounded_not_flagged(tmp_path):
    from scripts.lint_epistemic_precision import lint_epistemic_precision
    text = (
        "The latency stays within 5% of the baseline under nominal load. "
        "In cases where the source has been verified, the claim is admitted."
    )
    findings = lint_epistemic_precision(_write(tmp_path, text))
    cats = {f["category"] for f in findings}
    assert "banned_vague" not in cats
    assert "required_uncertainty" not in cats


def test_required_uncertainty_flagged(tmp_path):
    from scripts.lint_epistemic_precision import lint_epistemic_precision
    text = "The team shipped 47 features in the third quarter of 2024."
    findings = lint_epistemic_precision(_write(tmp_path, text))
    cats = {f["category"] for f in findings}
    assert "required_uncertainty" in cats


def test_required_uncertainty_suppressed_when_source_present(tmp_path):
    from scripts.lint_epistemic_precision import lint_epistemic_precision
    text = "The team shipped 47 features in the third quarter of 2024 (source: internal release log)."
    findings = lint_epistemic_precision(_write(tmp_path, text))
    cats = {f["category"] for f in findings}
    assert "required_uncertainty" not in cats
