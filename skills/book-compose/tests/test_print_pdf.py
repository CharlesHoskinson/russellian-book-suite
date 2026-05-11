from pathlib import Path
import pytest
from scripts.print_pdf import print_pdf, PrintPdfError
from scripts._playwright_check import is_playwright_ready

playwright_required = pytest.mark.skipif(
    not is_playwright_ready(),
    reason="Playwright + Chromium not installed (run `playwright install chromium`)",
)


@playwright_required
def test_print_pdf_creates_file(tmp_path):
    html = tmp_path / "src.html"
    html.write_text("<html><body><h1>Title</h1><p>Body.</p></body></html>", encoding="utf-8")
    out = tmp_path / "out.pdf"
    result = print_pdf(html, out)
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 1000  # at least 1KB for a real PDF


@playwright_required
def test_print_pdf_handles_multipage(tmp_path):
    html = tmp_path / "src.html"
    html.write_text(
        "<html><head><style>h1{page-break-before:always}h1:first-of-type{page-break-before:avoid}</style></head>"
        "<body>" + "".join(f"<h1>Chapter {i}</h1><p>{'word ' * 200}</p>" for i in range(5)) + "</body></html>",
        encoding="utf-8",
    )
    out = tmp_path / "out.pdf"
    print_pdf(html, out)
    assert out.stat().st_size > 5000


def test_print_pdf_raises_when_html_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        print_pdf(tmp_path / "missing.html", tmp_path / "out.pdf")
