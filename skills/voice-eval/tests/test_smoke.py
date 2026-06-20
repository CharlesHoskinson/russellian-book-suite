# skills/voice-eval/tests/test_smoke.py
"""Cites REQ-VEVAL-009 (skill scaffold)."""
import pytest

pytestmark = pytest.mark.windows_canary


def test_skill_api_version():
    import skill_api
    assert skill_api.API_VERSION == (0, 1)
