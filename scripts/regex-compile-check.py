#!/usr/bin/env python3
"""scripts/regex-compile-check.py — fail-fast if a lifts.edn pattern
won't compile under Python's `re`. Catches sprint-5 bug #7 (JS-style
`(?<name>...)` vs Python `(?P<name>...)`).

Usage: regex-compile-check.py <lifts.edn> [<lifts.edn> ...]

Returns 0 if every `:when` pattern compiles; non-zero on first failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Match (?<name> that is NOT (?P<name> — i.e. the JS-only form.
_JS_ONLY = re.compile(r"\(\?<(?!P)")


def _extract_when_patterns(text: str) -> list[str]:
    # Naive but sufficient: find every :when "..." form and return the
    # quoted string. EDN's quoting is simple: \\ and \" inside the string.
    out: list[str] = []
    i = 0
    while True:
        j = text.find(":when", i)
        if j < 0:
            break
        # Find the next quoted string
        k = text.find('"', j)
        if k < 0:
            break
        # Find the closing quote, respecting \\ and \"
        m = k + 1
        while m < len(text):
            c = text[m]
            if c == "\\":
                m += 2
                continue
            if c == '"':
                break
            m += 1
        if m >= len(text):
            break
        out.append(text[k + 1 : m])
        i = m + 1
    return out


def check_one(path: Path) -> list[str]:
    """Return list of error strings; empty on success."""
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for pat in _extract_when_patterns(text):
        # 1. JS-only named groups are an immediate fail.
        if _JS_ONLY.search(pat):
            errors.append(
                f"{path}: pattern uses JS-style (?<name>...) — "
                f"Python `re` requires (?P<name>...). Pattern: {pat!r}"
            )
            continue
        # 2. Try compiling as actual Python regex.
        try:
            # Decode EDN string escapes (\\ → \).
            decoded = pat.encode("utf-8").decode("unicode_escape")
            re.compile(decoded)
        except re.error as exc:
            errors.append(f"{path}: regex {pat!r} won't compile: {exc}")
    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: regex-compile-check.py <lifts.edn> [...]", file=sys.stderr)
        return 2
    all_errors: list[str] = []
    for arg in argv:
        all_errors.extend(check_one(Path(arg)))
    if all_errors:
        for e in all_errors:
            print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
