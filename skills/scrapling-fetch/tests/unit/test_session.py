import pytest
from scripts.session import build_session, SessionMode


def _browser_deps_available() -> bool:
    """Stealth/Dynamic modes require patchright + msgspec (optional browser deps)."""
    try:
        import patchright  # noqa: F401
        import msgspec  # noqa: F401
        return True
    except ImportError:
        return False


_skip_browser = pytest.mark.skipif(
    not _browser_deps_available(),
    reason="patchright/msgspec not installed; skipping browser-mode session tests",
)


def test_build_session_plain_returns_fetcher():
    s = build_session(SessionMode.PLAIN)
    assert s is not None
    assert "Fetcher" in s.__class__.__name__ or "Session" in s.__class__.__name__


@_skip_browser
def test_build_session_stealth_returns_stealthy():
    s = build_session(SessionMode.STEALTH)
    assert "Stealth" in s.__class__.__name__


@_skip_browser
def test_build_session_dynamic_returns_dynamic():
    s = build_session(SessionMode.DYNAMIC)
    assert "Dynamic" in s.__class__.__name__
