"""lint_burstiness: Fano factor + AI-band proportion on sentence-length distribution."""
import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_uniform_short_sentences_flagged(tmp_path):
    from scripts.lint_burstiness import lint_burstiness
    text = " ".join([
        "This sentence has exactly fourteen words and sits inside the suspect AI band cleanly.",
        "Another sentence with fifteen words lands inside the same narrow predictable AI band today.",
        "Yet another sentence of thirteen words drops squarely inside the AI signature band.",
        "A fourth sentence reaches fourteen words again inside the suspect AI signature band.",
    ])
    findings = lint_burstiness(_write(tmp_path, text))
    assert findings
    f = findings[0]
    assert f["rule"] == "burstiness"
    assert f["in_band_proportion"] >= 0.75
    assert f["fano_factor"] < 0.5


def test_high_variance_passes(tmp_path):
    from scripts.lint_burstiness import lint_burstiness
    text = " ".join([
        "Short.",
        "A modest middle sentence holds the centre of the passage and points outward.",
        "Then comes a long, balanced, compound-complex sentence that uses subordination, a parenthetical aside (offered here), and a closing turn to demonstrate the variance that human prose carries against the metronomic AI rhythm those who read closely come to recognise.",
        "Brief again.",
        "A normal sentence of eight words follows neatly.",
        "Final sentence runs to twenty-two words to balance the earlier short ones and to lift the section's Fano factor well above the AI signature threshold.",
    ])
    findings = lint_burstiness(_write(tmp_path, text))
    if findings:
        f = findings[0]
        assert f["fano_factor"] >= 0.5


def test_empty_document_returns_empty(tmp_path):
    from scripts.lint_burstiness import lint_burstiness
    findings = lint_burstiness(_write(tmp_path, ""))
    assert findings == []


def test_single_sentence_returns_empty(tmp_path):
    from scripts.lint_burstiness import lint_burstiness
    findings = lint_burstiness(_write(tmp_path, "Single sentence here."))
    assert findings == []
