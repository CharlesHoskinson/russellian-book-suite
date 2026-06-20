"""Cites REQ-LIVE-001 (skill scaffold)."""
import pytest
pytestmark = pytest.mark.windows_canary


def test_skill_api_version():
    import skill_api
    assert skill_api.API_VERSION == (0, 1)
