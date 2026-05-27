"""Clean-content extraction: fetched HTML -> readable markdown / prose paragraphs.

Mirrors the llm-wiki extraction methodology (Scrapling fetch + trafilatura), adapted
to reuse this skill's own fetch(). The trafilatura and fetch imports are deferred so
the pure paragraph splitter imports and unit-tests without network or extra deps.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass

DEFAULT_MIN_WORDS = 30


@dataclass
class Extraction:
    url: str
    markdown: str
    paragraphs: list[str]


def html_to_markdown(html: str, url: str = "") -> str:
    """Extract main-content markdown from HTML via trafilatura (deferred import).

    Boilerplate (nav, headers, footers, comments) is removed; the readable body is
    returned as markdown. Returns "" when nothing extractable is found.
    """
    import trafilatura
    return trafilatura.extract(
        html,
        output_format="markdown",
        favor_precision=True,
        include_comments=False,
        include_tables=False,
        deduplicate=True,
        url=url or None,
    ) or ""


def markdown_to_paragraphs(markdown: str, min_words: int = DEFAULT_MIN_WORDS) -> list[str]:
    """Split clean markdown into substantial prose paragraphs (stdlib-only, deterministic).

    Skips headings, list items, block quotes, tables, and code fences; collapses
    internal whitespace; keeps blocks with at least ``min_words`` words.
    """
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", markdown):
        block = block.strip()
        if not block:
            continue
        if block[0] in "#>|" or block.startswith(("- ", "* ", "+ ", "```")) or re.match(r"^\d+\.", block):
            continue
        text = " ".join(block.split())
        if len(text.split()) >= min_words:
            paragraphs.append(text)
    return paragraphs


def extract_paragraphs(url: str, *, mode: str = "plain",
                       min_words: int = DEFAULT_MIN_WORDS) -> Extraction:
    """Fetch a URL through this skill's fetch() and return clean prose paragraphs (network)."""
    from scripts.fetch import fetch
    page = fetch(url, mode=mode)
    markdown = html_to_markdown(page.html, url)
    return Extraction(url=url, markdown=markdown,
                      paragraphs=markdown_to_paragraphs(markdown, min_words))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: extract.py <url> [min_words]", file=sys.stderr)
        return 2
    min_words = int(argv[2]) if len(argv) > 2 else DEFAULT_MIN_WORDS
    result = extract_paragraphs(argv[1], min_words=min_words)
    print(f"{len(result.paragraphs)} paragraphs ({len(result.markdown.split())} words) from {result.url}")
    for i, p in enumerate(result.paragraphs[:3], 1):
        print(f"[{i}] {p[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
