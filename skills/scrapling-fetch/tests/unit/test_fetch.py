import pytest
from scripts.fetch import fetch, Page
from scripts.exceptions import (
    OfflineMiss, RateLimitExceeded, BlockedRequest, FetchFailed,
)


def _fake_session(status: int, html: str = "<html></html>"):
    class FakeResp:
        url = "https://example.org/"
        status_code = status
        html_content = html
    FakeResp.status = status
    FakeResp.html = html
    FakeResp.headers = {"content-type": "text/html"}
    class FakeSession:
        def get(self, url, **kw): return FakeResp()
    return FakeSession()


def test_fetch_returns_page_on_2xx(monkeypatch):
    monkeypatch.setattr("scripts.fetch._session_for_mode", lambda m: _fake_session(200))
    p = fetch("https://example.org/")
    assert isinstance(p, Page)
    assert p.status == 200
    assert p.html == "<html></html>"


def test_fetch_offline_raises(monkeypatch):
    monkeypatch.setenv("SCRAPLING_OFFLINE", "1")
    with pytest.raises(OfflineMiss):
        fetch("https://example.org/")


def test_fetch_429_raises_rate_limit_exceeded(monkeypatch):
    monkeypatch.setattr("scripts.fetch._session_for_mode", lambda m: _fake_session(429))
    with pytest.raises(RateLimitExceeded):
        fetch("https://example.org/")


def test_fetch_403_raises_blocked_request(monkeypatch):
    monkeypatch.setattr("scripts.fetch._session_for_mode", lambda m: _fake_session(403))
    with pytest.raises(BlockedRequest):
        fetch("https://example.org/")


def test_fetch_500_raises_fetch_failed(monkeypatch):
    monkeypatch.setattr("scripts.fetch._session_for_mode", lambda m: _fake_session(500))
    with pytest.raises(FetchFailed):
        fetch("https://example.org/")


def test_fetch_404_raises_fetch_failed(monkeypatch):
    monkeypatch.setattr("scripts.fetch._session_for_mode", lambda m: _fake_session(404))
    with pytest.raises(FetchFailed):
        fetch("https://example.org/")


def test_fetch_session_exception_wraps_as_fetch_failed(monkeypatch):
    class BoomSession:
        def get(self, url, **kw): raise ConnectionError("network down")
    monkeypatch.setattr("scripts.fetch._session_for_mode", lambda m: BoomSession())
    with pytest.raises(FetchFailed) as exc:
        fetch("https://example.org/")
    assert "network down" in str(exc.value)


# ---------------------------------------------------------------------------
# Regression tests for the Scrapling 0.4.8 API shape.
#
# Scrapling 0.4.8's `FetcherSession` exposes `.get` only after `__enter__`
# returns a (potentially different) entered object, and the resulting response
# carries the HTML body on `html_content` rather than `html`. Both shapes are
# load-bearing for every adapter that calls `fetch()`.
# ---------------------------------------------------------------------------

def test_session_for_mode_enters_lazy_session(monkeypatch):
    """`_session_for_mode` must enter a context-managed session even when the
    object it caches appears to have `.get` — a wrapper's `.get` can delegate
    to an un-entered inner, so `hasattr(wrapper, 'get')` is not a sufficient
    readiness signal."""
    from scripts import fetch as fetch_mod
    from scripts.session import _RateLimitedSession

    class _EnteredFetcher:
        """Scrapling 0.4.8 returns a fresh object from __enter__ that
        exposes `.get`."""
        def get(self, url, **kw):
            return type("R", (), {
                "status": 200,
                "html_content": "<ok/>",
                "url": url,
                "headers": {},
            })()

    class LazyFetcher:
        """Mirrors Scrapling 0.4.8 pre-entry shape: no `.get` defined."""
        def __enter__(self): return _EnteredFetcher()
        def __exit__(self, *a): pass

    wrapped = _RateLimitedSession(LazyFetcher())
    monkeypatch.setattr("scripts.fetch.build_session", lambda mode: wrapped)
    fetch_mod._session_cache.clear()
    try:
        page = fetch_mod.fetch("https://example.org/")
    finally:
        fetch_mod._session_cache.clear()
    assert page.status == 200


def test_fetch_reads_html_content_when_html_attribute_missing(monkeypatch):
    """Scrapling 0.4.8 response objects expose the HTML body on
    `html_content`. `fetch()` must populate `Page.html` from there."""
    class Resp:
        url = "https://example.org/"
        status = 200
        html_content = "<scrapling-0.4.8-body/>"
        headers = {}
    class Session:
        def get(self, url, **kw): return Resp()
    monkeypatch.setattr("scripts.fetch._session_for_mode", lambda m: Session())
    p = fetch("https://example.org/")
    assert p.html == "<scrapling-0.4.8-body/>"
