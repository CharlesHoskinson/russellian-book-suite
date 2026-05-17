from scripts.fetch import fetch, Page

def test_fetch_returns_page(monkeypatch):
    class FakeResp:
        url = "https://example.org/"
        status = 200
        html = "<html></html>"
        headers = {"content-type": "text/html"}
    class FakeSession:
        def get(self, url, **kw): return FakeResp()
    monkeypatch.setattr("scripts.fetch._session_for_mode", lambda m: FakeSession())
    p = fetch("https://example.org/")
    assert isinstance(p, Page)
    assert p.status == 200
    assert p.html == "<html></html>"

def test_fetch_offline_raises(monkeypatch):
    monkeypatch.setenv("SCRAPLING_OFFLINE", "1")
    from scripts.exceptions import OfflineMiss
    import pytest
    with pytest.raises(OfflineMiss):
        fetch("https://example.org/")
