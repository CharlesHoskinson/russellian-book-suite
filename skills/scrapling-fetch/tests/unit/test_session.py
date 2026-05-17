import pytest
from scripts.session import build_session, SessionMode

def test_build_session_plain_returns_fetcher():
    s = build_session(SessionMode.PLAIN)
    assert s is not None
    assert "Fetcher" in s.__class__.__name__ or "Session" in s.__class__.__name__

def test_build_session_stealth_returns_stealthy():
    s = build_session(SessionMode.STEALTH)
    assert "Stealth" in s.__class__.__name__

def test_build_session_dynamic_returns_dynamic():
    s = build_session(SessionMode.DYNAMIC)
    assert "Dynamic" in s.__class__.__name__
