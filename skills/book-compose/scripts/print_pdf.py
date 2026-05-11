"""Render an HTML file to PDF using headless Chromium via Playwright.

Used by build_book to convert manuscript.html into manuscript.pdf. The HTML
must include @media print rules (or Tailwind print: variants) to hide
interactive UI during the render.
"""
from __future__ import annotations

from pathlib import Path

from ._playwright_check import is_playwright_ready


class PrintPdfError(Exception):
    pass


def print_pdf(html_path: Path, out_path: Path) -> Path:
    html_path = Path(html_path)
    out_path = Path(out_path)
    if not html_path.is_file():
        raise FileNotFoundError(f"html not found: {html_path}")
    if not is_playwright_ready():
        raise PrintPdfError(
            "Playwright + Chromium not available. Run `playwright install chromium`."
        )

    from playwright.sync_api import sync_playwright

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            file_url = "file:///" + str(html_path.resolve()).replace("\\", "/")
            page.goto(file_url, wait_until="networkidle")
            page.emulate_media(media="print")
            page.pdf(
                path=str(out_path),
                format="A4",
                margin={"top": "25mm", "right": "20mm", "bottom": "25mm", "left": "20mm"},
                print_background=True,
                display_header_footer=True,
                header_template="<div></div>",
                footer_template=(
                    '<div style="font-size:9px;width:100%;text-align:center;color:#666;">'
                    '<span class="pageNumber"></span> / <span class="totalPages"></span>'
                    "</div>"
                ),
            )
        finally:
            browser.close()
    return out_path
