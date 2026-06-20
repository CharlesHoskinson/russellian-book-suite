# skills/voice-eval/tests/test_smoke.py
"""Cites REQ-VEVAL-009 (skill scaffold)."""
import pytest

pytestmark = pytest.mark.windows_canary


def test_skill_api_version():
    import skill_api
    assert skill_api.API_VERSION == (0, 1)


def test_skill_md_documents_the_protocol():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text(encoding="utf-8")
    for anchor in ("20×20", "in-session", "blind", "order", "floor", "win-rate"):
        assert anchor in text, f"SKILL.md must mention {anchor!r}"
