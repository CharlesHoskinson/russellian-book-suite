import pytest
from scripts.session import (
    build_session, SessionMode,
    DEFAULT_TIMEOUT_S, DEFAULT_RETRIES, DEFAULT_RETRY_DELAY_S,
    DEFAULT_IMPERSONATE, DEFAULT_STEALTHY_HEADERS,
    PER_HOST_MIN_DELAY_S,
    _RateLimitedSession, _enforce_per_host_delay,
    _last_request_by_host,
)


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


def test_build_session_plain_returns_rate_limited_fetcher():
    s = build_session(SessionMode.PLAIN)
    assert isinstance(s, _RateLimitedSession)
    inner = s._inner
    assert "Fetcher" in inner.__class__.__name__ or "Session" in inner.__class__.__name__


def test_plain_session_passes_politeness_kwargs_to_fetcher(monkeypatch):
    """REQ-SF-3: politeness defaults are explicitly wired on FetcherSession,
    not relying on Scrapling's silent defaults. We spy on the constructor."""
    captured: dict = {}

    class SpyFetcher:
        def __init__(self, **kwargs):
            captured.update(kwargs)
        def __enter__(self): return self
        def __exit__(self, *a): pass

    # build_session imports FetcherSession lazily inside the function, so we
    # patch the symbol where it is looked up.
    import scrapling.engines.static as static_mod
    monkeypatch.setattr(static_mod, "FetcherSession", SpyFetcher)
    s = build_session(SessionMode.PLAIN)
    assert isinstance(s, _RateLimitedSession)
    assert captured["timeout"] == DEFAULT_TIMEOUT_S
    assert captured["retries"] == DEFAULT_RETRIES
    assert captured["retry_delay"] == DEFAULT_RETRY_DELAY_S
    assert captured["impersonate"] == DEFAULT_IMPERSONATE
    assert captured["stealthy_headers"] == DEFAULT_STEALTHY_HEADERS


def test_per_host_rate_limiter_sleeps_between_same_host_requests(monkeypatch):
    """Two consecutive requests to the same host trigger a sleep on the second."""
    sleeps: list[float] = []
    monkeypatch.setattr("scripts.session.time.sleep", lambda s: sleeps.append(s))
    _last_request_by_host.clear()
    _enforce_per_host_delay("https://example.org/a")
    _enforce_per_host_delay("https://example.org/b")
    assert len(sleeps) == 1, f"expected 1 sleep, got {sleeps}"
    assert 0 < sleeps[0] <= PER_HOST_MIN_DELAY_S


def test_per_host_rate_limiter_does_not_sleep_across_hosts(monkeypatch):
    """Requests to different hosts don't throttle each other."""
    sleeps: list[float] = []
    monkeypatch.setattr("scripts.session.time.sleep", lambda s: sleeps.append(s))
    _last_request_by_host.clear()
    _enforce_per_host_delay("https://a.example.org/x")
    _enforce_per_host_delay("https://b.example.org/x")
    assert sleeps == []


def test_rate_limited_session_forwards_unknown_attrs():
    class Fake:
        def __init__(self): self.x = 42
        def foo(self): return "ok"
    w = _RateLimitedSession(Fake())
    assert w.x == 42
    assert w.foo() == "ok"


def test_rate_limited_session_get_invokes_throttle(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("scripts.session.time.sleep", lambda s: sleeps.append(s))
    _last_request_by_host.clear()

    class Fake:
        def get(self, url, **kw): return ("got", url)
    w = _RateLimitedSession(Fake())
    w.get("https://example.org/1")
    w.get("https://example.org/2")
    assert len(sleeps) == 1


@_skip_browser
def test_build_session_stealth_returns_stealthy():
    s = build_session(SessionMode.STEALTH)
    inner = s._inner if isinstance(s, _RateLimitedSession) else s
    assert "Stealth" in inner.__class__.__name__


@_skip_browser
def test_build_session_dynamic_returns_dynamic():
    s = build_session(SessionMode.DYNAMIC)
    inner = s._inner if isinstance(s, _RateLimitedSession) else s
    assert "Dynamic" in inner.__class__.__name__
