"""Convert GFM footnote syntax in markdown to HTML for marked.js consumption.

Per-chapter numbering: footnote numbers reset at each `# Chapter N:` heading.
The chapter author adds a `## Notes` section at the end of the chapter
containing `[^name]: definition` blocks; this script:

1. finds each chapter,
2. collects `[^name]` references in order of appearance,
3. assigns 1..N numbering within the chapter,
4. replaces inline `[^name]` with `<sup class="footnote-ref" id="fnref-CH-NAME"><a href="#fn-CH-NAME">N</a></sup>`,
5. replaces the `## Notes` block with a `<section class="footnotes">...<ol>...</ol></section>` block.
"""
from __future__ import annotations
import re
from pathlib import Path


CHAPTER_RE = re.compile(r"^(# Chapter (\d+):.*)$", re.MULTILINE)
FOOTNOTE_REF_RE = re.compile(r"\[\^([a-zA-Z0-9_-]+)\]")
NOTES_HEADING_RE = re.compile(r"^## Notes\s*$", re.MULTILINE)
DEF_RE = re.compile(
    r"^\[\^([a-zA-Z0-9_-]+)\]:\s*((?:.+(?:\n(?:    .+|\t.+))*))",
    re.MULTILINE,
)


def _process_chapter(body: str, chapter_num: int) -> str:
    # Split body into prose section and notes section
    notes_match = NOTES_HEADING_RE.search(body)
    if notes_match:
        prose = body[: notes_match.start()]
        notes_block = body[notes_match.end():]
    else:
        prose = body
        notes_block = ""

    # Collect refs in order of appearance in prose
    seen: dict[str, int] = {}
    order: list[str] = []
    for m in FOOTNOTE_REF_RE.finditer(prose):
        name = m.group(1)
        if name not in seen:
            seen[name] = len(order) + 1
            order.append(name)

    if not order:
        return body  # no footnotes

    # Build name → definition dict from notes block
    definitions: dict[str, str] = {}
    for m in DEF_RE.finditer(notes_block):
        name = m.group(1)
        text = re.sub(r"\n\s+", " ", m.group(2)).strip()
        definitions[name] = text

    # Replace inline refs in prose
    def _ref_repl(match: re.Match) -> str:
        name = match.group(1)
        if name not in seen:
            return match.group(0)
        n = seen[name]
        return (
            f'<sup class="footnote-ref" id="fnref-ch{chapter_num:02d}-{name}">'
            f'<a href="#fn-ch{chapter_num:02d}-{name}">{n}</a></sup>'
        )

    new_prose = FOOTNOTE_REF_RE.sub(_ref_repl, prose)

    # Build the HTML notes section
    items = []
    for name in order:
        seen[name]
        text = definitions.get(name, f"<em>(definition for {name} missing)</em>")
        items.append(
            f'<li id="fn-ch{chapter_num:02d}-{name}">'
            f'<p>{text} '
            f'<a href="#fnref-ch{chapter_num:02d}-{name}" class="footnote-back" aria-label="back to text">↩</a>'
            f'</p></li>'
        )
    html_notes = (
        '\n\n<section class="footnotes" role="doc-endnotes">\n'
        '<h2 class="footnotes-heading">Notes</h2>\n'
        '<ol>\n' + "\n".join(items) + "\n</ol>\n</section>\n\n"
    )

    return new_prose.rstrip() + html_notes


def process_manuscript(text: str) -> str:
    """Split manuscript by chapter heading, process each chapter, recombine."""
    # Find all chapter heading positions
    positions = [(m.start(), m.group(0), int(m.group(2)))
                 for m in CHAPTER_RE.finditer(text)]
    if not positions:
        return text

    out_parts: list[str] = []
    # Content before first chapter
    out_parts.append(text[: positions[0][0]])

    for i, (start, heading, num) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        body = text[start:end]
        out_parts.append(_process_chapter(body, num))

    return "".join(out_parts)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("usage: process_footnotes.py <manuscript.md>", file=sys.stderr)
        sys.exit(2)
    p = Path(sys.argv[1])
    text = p.read_text(encoding="utf-8")
    new = process_manuscript(text)
    p.write_text(new, encoding="utf-8")
    # Count footnotes added
    count = new.count('class="footnote-ref"')
    print(f"processed {p.name}: {count} footnote refs inlined")
