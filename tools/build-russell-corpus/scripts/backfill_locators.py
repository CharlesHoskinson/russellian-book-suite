"""One-time migration: backfill the canonical content_locator onto index entries.

The 50 committed seed entries in skills/russellian-style/assets/russell-corpus/index.json
predate the content_locator field — they carry only id/source/line_hint/rhetorical_move/
tags. Without a content_locator, the sentinel's canonical-locator dedup branch (Check 4a)
cannot recognise a re-extracted seed paragraph as a duplicate (finding
sentinel-seed-entries-have-no-locator).

This migration derives the canonical key — content_locator(paragraph_text), i.e. the first
120 stripped chars of the paragraph — by reading the cached source HTML for each entry's
source and extracting the <p> block at the entry's line_hint, then stores it under
"content_locator" on the entry. It is idempotent: entries that already carry a
content_locator are left untouched.

Run it once whenever the cached Gutenberg sources are available locally:

    python -m scripts.backfill_locators \\
        --index ../../skills/russellian-style/assets/russell-corpus/index.json \\
        --source-cache <dir-of-cached-source-html>

Entries whose source HTML is not present in the cache, or whose line_hint does not resolve
to a <p> block, are reported and skipped (never fabricated) so the migration can be re-run
as more sources become cached. Until an entry is backfilled, the (source, line_hint)
position key in the sentinel still protects it from re-admission.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

from scripts.corpus_io import content_locator, read_index


_TAG_RE = re.compile(r"<[^>]+>")


def _paragraph_at_line(source_text: str, line_hint: int) -> str | None:
    """Extract the text of the <p> block that opens at or after `line_hint`.

    Real Gutenberg HTML wraps a single paragraph across many ~70-char physical lines, so a
    paragraph that opens on `line_hint` may continue for several lines until `</p>`. We scan
    from the 1-indexed line_hint forward to the first line containing "<p", accumulate text
    through the matching "</p>", strip HTML tags, and collapse whitespace.

    Returns None if no <p> block can be resolved from line_hint (caller skips the entry).
    """
    lines = source_text.splitlines()
    if line_hint < 1 or line_hint > len(lines):
        return None
    # Find the <p> opening tag at or just after the hinted line (line numbers drift across
    # editions, so allow a small forward window rather than requiring an exact match).
    start = None
    for i in range(line_hint - 1, min(len(lines), line_hint - 1 + 5)):
        if "<p" in lines[i].lower():
            start = i
            break
    if start is None:
        return None
    buf: list[str] = []
    for i in range(start, len(lines)):
        buf.append(lines[i])
        if "</p>" in lines[i].lower():
            break
    html = " ".join(buf)
    text = _TAG_RE.sub(" ", html)
    text = " ".join(text.split())
    return text or None


def backfill_content_locators(
    *,
    index_path: Path,
    source_cache_dir: Path,
    cache_filename: Callable[[str], str] = lambda sid: f"{sid}.html",
) -> int:
    """Backfill content_locator onto every entry that lacks one, in place and atomically.

    Returns the number of entries newly backfilled. Idempotent: entries that already carry
    a content_locator are skipped, so re-running returns 0. Entries whose source HTML is
    absent or whose line_hint does not resolve to a <p> block are skipped (reported to
    stderr) and never assigned a fabricated locator.
    """
    idx = read_index(index_path)
    source_text_cache: dict[str, str | None] = {}
    updated = 0
    skipped: list[str] = []

    for entry in idx["paragraphs"]:
        if entry.get("content_locator"):
            continue
        source_id = entry.get("source")
        line_hint = entry.get("line_hint")
        if source_id is None or line_hint is None:
            skipped.append(f"{entry.get('id')}: missing source/line_hint")
            continue
        if source_id not in source_text_cache:
            src_file = source_cache_dir / cache_filename(source_id)
            source_text_cache[source_id] = (
                src_file.read_text(encoding="utf-8") if src_file.exists() else None
            )
        source_text = source_text_cache[source_id]
        if source_text is None:
            skipped.append(f"{entry.get('id')}: no cached source for {source_id!r}")
            continue
        paragraph = _paragraph_at_line(source_text, int(line_hint))
        if not paragraph:
            skipped.append(f"{entry.get('id')}: no <p> at line {line_hint}")
            continue
        entry["content_locator"] = content_locator(paragraph)
        updated += 1

    if updated:
        tmp = index_path.with_suffix(index_path.suffix + ".tmp")
        tmp.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(index_path)

    if skipped:
        print(
            f"backfill_locators: skipped {len(skipped)} entr"
            f"{'y' if len(skipped) == 1 else 'ies'} (not fabricated):",
            file=sys.stderr,
        )
        for line in skipped:
            print(f"  - {line}", file=sys.stderr)

    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill content_locator onto corpus index entries.")
    parser.add_argument("--index", required=True, type=Path, help="Path to russell-corpus index.json")
    parser.add_argument(
        "--source-cache",
        required=True,
        type=Path,
        help="Directory of cached source HTML, one file per source_id",
    )
    parser.add_argument(
        "--cache-suffix",
        default=".html",
        help="Suffix appended to source_id to find each cached file (default: .html)",
    )
    args = parser.parse_args(argv)
    n = backfill_content_locators(
        index_path=args.index,
        source_cache_dir=args.source_cache,
        cache_filename=lambda sid: f"{sid}{args.cache_suffix}",
    )
    print(f"backfilled content_locator onto {n} entr{'y' if n == 1 else 'ies'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
