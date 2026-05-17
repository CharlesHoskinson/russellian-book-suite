from scripts.adapters import doi as doi_mod
from scripts.adapters.doi import resolve, ResolvedDoi

def test_resolve_returns_final_url(monkeypatch):
    class FakePage:
        final_url = "https://link.springer.com/article/10.1007/s00145-021-09382-3"
        headers = {"content-type": "text/html"}
        html = ""
    monkeypatch.setattr(doi_mod, "_fetch_doi", lambda d: FakePage())
    r = resolve("10.1007/s00145-021-09382-3")
    assert isinstance(r, ResolvedDoi)
    assert "springer" in r.final_url
