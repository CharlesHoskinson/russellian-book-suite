"""Splice the 4 hero-table HTML fragments into the chapter drafts,
replacing the existing markdown tables.

Each chapter has a markdown table whose header row uniquely identifies it.
We delete from that header line through the contiguous markdown table block
and insert the HTML fragment in its place.
"""
import re
from pathlib import Path

CH = Path("C:/bermuda-manual/chapters/drafts")
ASSETS = Path("C:/bermuda-manual/chapters/assets/shared/tables")

# Pattern: (chapter, header-identifier-substring, html-fragment-filename)
# Match by a row UNIQUE to each table — the first content row.
REPLACEMENTS = [
    ("ch-06", "| Rent, 1-bedroom outside Hamilton |", "ch-06-single-budget.html"),
    ("ch-06", "| Rent, 3-bedroom outside Hamilton |", "ch-06-family-budget.html"),
    ("ch-07", "| Bermudian / status holder |", "ch-07-arv-brackets.html"),
    ("ch-09", "| HIP | Health Insurance Department |", "ch-09-insurance-products.html"),
]


def replace_table_containing(text: str, unique_row: str, html: str) -> str:
    """Find the markdown table block (contiguous |...| lines) that contains a
    line starting with `unique_row`, and replace the whole block (including
    the header and separator above) with `html`."""
    lines = text.splitlines(keepends=True)
    target = None
    for i, line in enumerate(lines):
        if line.startswith(unique_row):
            target = i
            break
    if target is None:
        return text
    # Walk back to find the start of the table block.
    start = target
    while start > 0 and lines[start - 1].startswith("|"):
        start -= 1
    # Walk forward to find the end.
    end = target + 1
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    new_lines = lines[:start] + [html + "\n\n"] + lines[end:]
    return "".join(new_lines)


for chapter, unique_row, fragment_name in REPLACEMENTS:
    draft = CH / chapter / "draft.md"
    text = draft.read_text(encoding="utf-8")
    html = (ASSETS / fragment_name).read_text(encoding="utf-8")
    new = replace_table_containing(text, unique_row, html)
    if new == text:
        print(f"WARN: {chapter} no replacement made for {fragment_name}")
    else:
        draft.write_text(new, encoding="utf-8")
        print(f"{chapter} <- {fragment_name}")
