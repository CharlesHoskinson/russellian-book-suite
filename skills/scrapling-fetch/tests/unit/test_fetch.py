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
