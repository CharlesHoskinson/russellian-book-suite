"""Write the deterministic HTML skeleton that the React app inserts into.

The skeleton inlines the book payload (summary + manuscript markdown) as
<script> blocks. The web-artifacts-builder-anthropic skill is later invoked
by Claude during book build to render the React+Tailwind+shadcn browser into
the #book-app-root element, replacing the BOOK_APP_INSERTION_POINT marker.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SKELETON_TEMPLATE = (ASSETS / "book-html-skeleton.html").read_text(encoding="utf-8")
INSERTION_MARKER = "<!-- BOOK_APP_INSERTION_POINT -->"

# Orphan claim-citation tokens must not leak into the merged HTML (CLAUDE.md).
_CITATION_PATTERN = re.compile(r"\[clm-\d{4}-\d{6}\]")


_SCRIPT_END_RE = re.compile(r"</(script)", re.IGNORECASE)


def _escape_for_script_block(text: str) -> str:
    """Escape </script in the manuscript text so the embedded script tag does not break.

    The HTML tokenizer matches the script-data end tag case-insensitively, so
    </SCRIPT and </Script would also close the block; neutralise every case.
    """
    return _SCRIPT_END_RE.sub(r"<\\/\1", text)


def write_html_skeleton(out_path: Path, summary: dict, manuscript_md: str) -> Path:
    payload_json = _CITATION_PATTERN.sub("", json.dumps(summary, indent=2))
    manuscript_md = _CITATION_PATTERN.sub("", manuscript_md)
    rendered = (
        SKELETON_TEMPLATE
        .replace("{{book_title}}", html.escape(summary.get("book_title", "Book")))
        .replace("{{book_payload_json}}", _escape_for_script_block(payload_json))
        .replace("{{manuscript_md}}", _escape_for_script_block(manuscript_md))
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    return out_path
