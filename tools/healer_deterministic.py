"""v5 Healer Batch A — deterministic remediations.

C6  Terminology canonicalisation (L.F. Wade, Town of St. George variants)
C9  Markdown table column alignment (--- -> ---: where header marks numeric)
C13/C2 Empty `## Notes` heading cleanup (when no footnote definitions follow)
C15 Line wrap to <=120 chars in prose paragraphs (preserves HTML blocks, tables, code)

Runs over all 10 chapter drafts.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

DRAFTS = Path("C:/bermuda-manual/chapters/drafts")


# ---------------------------------------------------------------- C6 terminology

CANONICAL_REWRITES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bL\.\s*F\.\s*Wade(?: International)?(?! Airport)\b"), "L. F. Wade International Airport"),
    (re.compile(r"\bL\.F\. Wade International Airport\b"), "L. F. Wade International Airport"),
    (re.compile(r"\bL\.F\. Wade\b"), "L. F. Wade"),
    (re.compile(r"\bL\.\s*F\.\s*Bermuda Airport\b"), "L. F. Wade International Airport"),
    (re.compile(r"\bTown of St\. George's\b"), "Town of St. George"),
]


def fix_c6(text: str) -> tuple[str, int]:
    n = 0
    for pat, repl in CANONICAL_REWRITES:
        new, k = pat.subn(repl, text)
        if k:
            n += k
            text = new
    return text, n


# ---------------------------------------------------------------- C9 table alignment

NUMERIC_COL_PATS = [
    re.compile(r"^\|\s*\$?[\d.,%-]+", re.MULTILINE),
]


def fix_c9_table(table_lines: list[str]) -> tuple[list[str], int]:
    """Given the lines of one markdown table, right-align numeric columns
    by changing `---` to `---:` in the separator row."""
    if len(table_lines) < 3:
        return table_lines, 0

    sep_row = table_lines[1]
    body_rows = table_lines[2:]
    if not re.match(r"^\|[\s|:-]+\|\s*$", sep_row):
        return table_lines, 0

    # Tokenise separator and body cells
    sep_cells = [c.strip() for c in sep_row.strip("|").split("|")]

    # Find numeric columns: every body row's cell value looks numeric (digits/$/%/commas)
    body_cells_per_col: list[list[str]] = [[] for _ in sep_cells]
    for row in body_rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        for j, c in enumerate(cells[:len(sep_cells)]):
            body_cells_per_col[j].append(c)

    numeric_token_re = re.compile(r"^\$?-?[\d.,%]+\$?$|^\$?-?\d[\d.,]*\s*(km2|km|mm|°C|m|years?)?$|^—$|^-$")
    changed = 0
    new_sep_cells = []
    for j, cell in enumerate(sep_cells):
        body = body_cells_per_col[j]
        non_empty = [c for c in body if c and c != "—" and c != "-"]
        if non_empty and all(numeric_token_re.match(c) for c in non_empty):
            if not cell.endswith(":"):
                new_sep_cells.append(cell.rstrip("-") + "---:" if not cell.endswith("---:") else cell)
                # Easier: just replace trailing dashes with `---:`
                new_sep_cells[-1] = re.sub(r"-+:?$", "---:", cell) if not cell.endswith(":") else cell
                if new_sep_cells[-1] != cell:
                    changed += 1
            else:
                new_sep_cells.append(cell)
        else:
            new_sep_cells.append(cell)

    if changed == 0:
        return table_lines, 0
    new_sep = "| " + " | ".join(new_sep_cells) + " |"
    return [table_lines[0], new_sep, *body_rows], changed


def fix_c9(text: str) -> tuple[str, int]:
    """Find every markdown table and right-align numeric columns."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    total = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s|:-]+\|", lines[i + 1]):
            # Start of a table
            block = [line]
            j = i + 1
            while j < len(lines) and lines[j].startswith("|"):
                block.append(lines[j])
                j += 1
            fixed, n = fix_c9_table(block)
            out.extend(fixed)
            total += n
            i = j
        else:
            out.append(line)
            i += 1
    return "\n".join(out) + ("\n" if text.endswith("\n") else ""), total


# ---------------------------------------------------------------- C13/C2 empty Notes

EMPTY_NOTES_RE = re.compile(r"\n##\s+Notes\s*\n+(?:---\s*\n)?\s*$")
# Also: ## Notes followed only by separator + EOF (or another major heading)


def fix_c13_c2(text: str) -> tuple[str, int]:
    if EMPTY_NOTES_RE.search(text):
        text = EMPTY_NOTES_RE.sub("\n", text)
        return text, 1
    # Match ## Notes immediately followed by another ## or # heading (no body in between)
    m = re.search(r"\n##\s+Notes\s*\n+(?=##? |\Z)", text)
    if m:
        text = text[:m.start()] + "\n" + text[m.end():]
        return text, 1
    return text, 0


# ---------------------------------------------------------------- C15 line wrap

HTML_LINE_RE = re.compile(r"^\s*<[a-zA-Z/!]")
TABLE_LINE_RE = re.compile(r"^\|")
FENCE_RE = re.compile(r"^(```|~~~)")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^[a-zA-Z0-9_-]+\]:\s")
HEADING_RE = re.compile(r"^#{1,6}\s")
HR_RE = re.compile(r"^---+\s*$")


def _wrap_paragraph(par: str, width: int = 100) -> str:
    """Wrap a single prose paragraph, preserving markdown inline elements
    (links, images, bold, italic) by treating the whole paragraph as
    word-tokenised text. textwrap.fill handles common cases."""
    par = par.rstrip()
    if not par or len(max(par.split("\n"), key=len)) <= width:
        return par
    # Join multi-line paragraphs into one and re-wrap
    joined = re.sub(r"\s+", " ", par)
    return textwrap.fill(
        joined,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )


def fix_c15(text: str, width: int = 100) -> tuple[str, int]:
    """Wrap prose paragraphs to <= width chars. Preserve:
    - Lines starting with HTML tag (`<`)
    - Markdown tables (`|`)
    - Footnote definitions (`[^name]: ...`) — wrap within continuation
    - Code fences (``` ... ```)
    - Headings, horizontal rules
    """
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    changes = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if in_fence:
            out.append(line)
            i += 1
            continue
        if (HTML_LINE_RE.match(line) or TABLE_LINE_RE.match(line)
                or HEADING_RE.match(line) or HR_RE.match(line)
                or not line.strip()):
            out.append(line)
            i += 1
            continue
        # Collect a paragraph: contiguous non-blank, non-special lines
        para_lines = [line]
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if (not nxt.strip()
                    or HTML_LINE_RE.match(nxt)
                    or TABLE_LINE_RE.match(nxt)
                    or HEADING_RE.match(nxt)
                    or HR_RE.match(nxt)
                    or FENCE_RE.match(nxt)
                    or FOOTNOTE_DEF_RE.match(nxt)):
                break
            para_lines.append(nxt)
            j += 1
        paragraph = "\n".join(para_lines)
        wrapped = _wrap_paragraph(paragraph, width=width)
        if wrapped != paragraph:
            changes += 1
        out.append(wrapped)
        i = j
    return "\n".join(out) + ("\n" if text.endswith("\n") else ""), changes


# ---------------------------------------------------------------- main

def main():
    summary = []
    for n in range(1, 11):
        path = DRAFTS / f"ch-{n:02d}" / "draft.md"
        text = path.read_text(encoding="utf-8")
        original_len = len(text)

        text, c6 = fix_c6(text)
        text, c9 = fix_c9(text)
        text, c13 = fix_c13_c2(text)
        text, c15 = fix_c15(text, width=100)

        if c6 + c9 + c13 + c15 > 0:
            path.write_text(text, encoding="utf-8")

        summary.append((f"ch-{n:02d}", c6, c9, c13, c15, original_len, len(text)))

    print(f"{'chapter':<8}{'C6':>4}{'C9':>4}{'C13':>4}{'C15':>5}  size (was -> now)")
    for ch, c6, c9, c13, c15, was, now in summary:
        print(f"{ch:<8}{c6:>4}{c9:>4}{c13:>4}{c15:>5}  {was:>6,} -> {now:,}")


if __name__ == "__main__":
    main()
