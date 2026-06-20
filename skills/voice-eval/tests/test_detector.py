# skills/voice-eval/tests/test_detector.py
"""Cites REQ-VEVAL-014 (detector advisory-only, never gates)."""
import pytest

pytestmark = pytest.mark.windows_canary


def test_detector_report_is_advisory_and_never_blocks():
    from scripts.detector import detector_report
    passages = [{"prompt_id": "P01", "arm": "v2", "text": "x"}]
    rep = detector_report(passages, scorer=lambda text: 0.99)   # "looks AI" — must NOT gate
    assert rep["advisory"] is True
    assert rep["gates"] is False
    assert rep["rows"][0]["score"] == 0.99
    assert "blocked" not in rep and "failures" not in rep


def test_detector_absent_scorer_is_noop():
    from scripts.detector import detector_report
    rep = detector_report([{"prompt_id": "P01", "arm": "v2", "text": "x"}], scorer=None)
    assert rep["advisory"] is True and rep["gates"] is False
    assert rep["rows"] == []
