
from scripts.render_book_html import write_html_skeleton, INSERTION_MARKER


def test_skeleton_contains_book_title(tmp_path):
    out = tmp_path / "manuscript.html"
    summary = {"book_id": "test", "book_title": "Test Book", "total_words": 100,
               "total_claims": 5, "chapters": [], "sources_bibliography": []}
    write_html_skeleton(out, summary, manuscript_md="# Test Book\n\nBody.\n")
    text = out.read_text(encoding="utf-8")
    assert "Test Book" in text
    assert INSERTION_MARKER in text


def test_skeleton_inlines_payload_json(tmp_path):
    out = tmp_path / "manuscript.html"
    summary = {"book_id": "test", "book_title": "Test Book", "total_words": 100,
               "total_claims": 5, "chapters": [{"chapter_id": "ch-01", "title": "Intro"}],
               "sources_bibliography": []}
    write_html_skeleton(out, summary, manuscript_md="# Intro")
    text = out.read_text(encoding="utf-8")
    start = text.find('id="book-payload"')
    assert start != -1
    block = text[start:start + 2000]
    assert '"chapter_id": "ch-01"' in block
    assert '"book_id": "test"' in block


def test_skeleton_inlines_manuscript_markdown(tmp_path):
    out = tmp_path / "manuscript.html"
    summary = {"book_id": "test", "book_title": "Test Book", "total_words": 100,
               "total_claims": 5, "chapters": [], "sources_bibliography": []}
    write_html_skeleton(out, summary, manuscript_md="# Intro\n\nFull text.\n")
    text = out.read_text(encoding="utf-8")
    assert 'id="book-manuscript"' in text
    assert "Full text." in text


def test_skeleton_html_parses(tmp_path):
    """Sanity check that the skeleton is well-formed HTML5."""
    from html.parser import HTMLParser

    class Validator(HTMLParser):
        def __init__(self):
            super().__init__()
            self.errors = []

        def error(self, msg):
            self.errors.append(msg)

    out = tmp_path / "manuscript.html"
    summary = {"book_id": "test", "book_title": "Test Book", "total_words": 100,
               "total_claims": 5, "chapters": [], "sources_bibliography": []}
    write_html_skeleton(out, summary, manuscript_md="x")
    parser = Validator()
    parser.feed(out.read_text(encoding="utf-8"))
    assert parser.errors == []
