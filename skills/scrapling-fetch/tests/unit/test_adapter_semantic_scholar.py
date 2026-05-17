from scripts.adapters import semantic_scholar
from scripts.adapters.openalex import PaperRef

def test_references_stubbed(monkeypatch):
    # The unit test stubs out the network — semantic_scholar's behavior against
    # live pages is exercised by the live suite.
    sample = """
    <html><body>
      <div data-test="paper-row">
        <a data-test="paper-title">First Cited Work</a>
        <span data-test="year">2021</span>
        <span data-test="citation-count">12</span>
      </div>
      <div data-test="paper-row">
        <a data-test="paper-title">Second Cited Work</a>
        <span data-test="year">2022</span>
        <span data-test="citation-count">3</span>
      </div>
    </body></html>
    """
    class FakePage:
        html = sample
        final_url = "https://www.semanticscholar.org/paper/foo/references"
    monkeypatch.setattr(semantic_scholar, "_fetch", lambda url: FakePage())
    refs = semantic_scholar.references("foo")
    assert len(refs) == 2
    assert refs[0].title == "First Cited Work"
    assert refs[0].year == 2021
    assert refs[0].citation_count == 12
