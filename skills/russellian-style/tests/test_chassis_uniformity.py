"""Cites REQ-VOICE-018, REQ-VOICE-019.

Filename is test_chassis_uniformity.py (NOT test_lint_*) so the conftest's
spaCy-absent collect_ignore_glob does not silently skip it in CI.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

from scripts.lint_chassis_uniformity import lint_chassis_uniformity


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


# Helper: a paragraph that classify_paragraph maps to a particular marker-hit shape.
_QUESTION_PARA = (
    "What is the snail's claim on us? It is the modest claim of a slow life "
    "lived to its own measure without insistence."
)
_CONCESSION_TURN_PARA = (
    "The defender will say the snail is merely slow, but the slowness is the point, "
    "and the point is not concession to weakness but care."
)
_CONTRAST_PARA = (
    "The snail moves at its own pace; however, the gardener moves at the seasons."
)
_EXAMPLE_INFERENCE_PARA = (
    "Consider the radula, with thousands of chitinous teeth. Therefore the snail "
    "is not unarmed, only quiet about its weapon."
)
_DEFINITION_BY_PRESSURE_PARA = (
    "As commonly used, slowness names a fault. Used more carefully, it names "
    "an unhurried attention that arrives at the same place by a steadier road."
)
_FALLBACK_PARA = (
    "The shell records the seasons. Each year adds its line in calcium. "
    "The animal carries a diary it cannot read."
)  # No marker → assertion_justification fallback


def _doc(*paras: str) -> str:
    return "\n\n".join(paras)


def test_three_in_a_row_streak_flags(tmp_path):
    text = _doc(_QUESTION_PARA, _QUESTION_PARA, _QUESTION_PARA, _FALLBACK_PARA)
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    streak = [f for f in findings if f["signal"] == "streak"]
    assert len(streak) >= 1
    assert streak[0]["shape"] == "question_answer"
    assert all(f["severity"] == "advisory" for f in findings)


def test_marker_hit_dominance_flags_in_window(tmp_path):
    # 5-paragraph window; 3 of 5 share a marker-hit shape.
    text = _doc(
        _CONCESSION_TURN_PARA,
        _FALLBACK_PARA,
        _CONCESSION_TURN_PARA,
        _FALLBACK_PARA,
        _CONCESSION_TURN_PARA,
    )
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    marker = [f for f in findings if f["signal"] == "marker_dominance"]
    assert len(marker) >= 1
    assert marker[0]["shape"] == "concession_turn"


def test_fallback_dominance_does_not_trigger_marker_signal(tmp_path):
    # 6 paragraphs of pure-fallback (no markers). The marker-hit dominance signal
    # must NOT fire — that was the first-draft failure mode (false-positive
    # saturation on Didion-style sparse-marker prose).
    text = _doc(*[_FALLBACK_PARA] * 6)
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    marker = [f for f in findings if f["signal"] == "marker_dominance"]
    assert marker == [], (
        f"marker_dominance must not fire on fallback-only prose; got {marker}"
    )
    # But the streak signal IS expected to fire (6 consecutive same-shape paragraphs).
    streak = [f for f in findings if f["signal"] == "streak"]
    assert len(streak) >= 1


def test_varied_marker_hit_paragraphs_do_not_flag(tmp_path):
    text = _doc(
        _QUESTION_PARA,
        _CONCESSION_TURN_PARA,
        _CONTRAST_PARA,
        _EXAMPLE_INFERENCE_PARA,
        _DEFINITION_BY_PRESSURE_PARA,
    )
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    marker = [f for f in findings if f["signal"] == "marker_dominance"]
    streak = [f for f in findings if f["signal"] == "streak"]
    assert marker == []
    assert streak == []


def test_low_entropy_flags(tmp_path):
    # 8 paragraphs, all the same fallback shape → entropy 0 < 1.5.
    text = _doc(*[_FALLBACK_PARA] * 8)
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    entropy = [f for f in findings if f["signal"] == "entropy"]
    assert len(entropy) == 1
    assert entropy[0]["entropy"] == 0.0


def test_high_entropy_does_not_flag(tmp_path):
    # 7 paragraphs spread across all 7 shapes → entropy ≈ log2(7) ≈ 2.81.
    text = _doc(
        _QUESTION_PARA, _CONCESSION_TURN_PARA, _CONTRAST_PARA,
        _EXAMPLE_INFERENCE_PARA, _DEFINITION_BY_PRESSURE_PARA,
        _FALLBACK_PARA, "Single.",
    )
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    entropy = [f for f in findings if f["signal"] == "entropy"]
    assert entropy == []


def test_closer_concentration_flags_at_threshold(tmp_path):
    # 10 paragraphs, 6 with humanity-token closers (60% ≥ 50% threshold, 10 ≥ 8 min).
    closer_p = (
        "Watch the crossing. We have invented a hundred narcotics against tedium."
    )
    plain_p = "The shell records the seasons. Each year adds its line in calcium."
    text = _doc(*([closer_p] * 6 + [plain_p] * 4))
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    closer = [f for f in findings if f["signal"] == "closer_concentration"]
    assert len(closer) == 1
    assert closer[0]["closer_proportion"] >= 0.5


def test_closer_concentration_does_not_flag_below_threshold(tmp_path):
    closer_p = (
        "Watch the crossing. We have invented a hundred narcotics against tedium."
    )
    plain_p = "The shell records the seasons. Each year adds its line in calcium."
    # 10 paragraphs, 3 closers (30% < 50%).
    text = _doc(*([closer_p] * 3 + [plain_p] * 7))
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    closer = [f for f in findings if f["signal"] == "closer_concentration"]
    assert closer == []


def test_short_document_skips_closer_concentration(tmp_path):
    closer_p = (
        "Watch the crossing. We have invented a hundred narcotics against tedium."
    )
    # 5 paragraphs (< 8 minimum) — closer_concentration must not fire even if all 5 are closers.
    text = _doc(*([closer_p] * 5))
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    closer = [f for f in findings if f["signal"] == "closer_concentration"]
    assert closer == []


def test_advisory_severity_only(tmp_path):
    text = _doc(*[_QUESTION_PARA] * 4)
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    assert findings
    assert all(f["severity"] == "advisory" for f in findings)


def test_determinism(tmp_path):
    text = _doc(_QUESTION_PARA, _QUESTION_PARA, _QUESTION_PARA, _FALLBACK_PARA)
    p = _write(tmp_path, text)
    assert lint_chassis_uniformity(p) == lint_chassis_uniformity(p)
