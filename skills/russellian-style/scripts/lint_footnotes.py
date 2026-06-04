"""Detect orphaned markdown footnotes.

Two failure modes, both deterministic and both invisible to the prose linters:
an inline ``[^label]`` marker with no matching ``[^label]:`` definition, and a
``[^label]:`` definition that no inline marker ever references. The second is the
one that slips through: a draft can carry a full set of footnote definitions and
none of the inline citations, passing every style gate while every footnote is
orphaned.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import load_markdown

# Footnote labels here are ids: word characters and hyphens, no spaces. Using a
# tight label class avoids matching regex character classes like ``[^abc]`` that
# can appear in prose about patterns.
_DEF_RE = re.compile(r"^[ \t]*\[\^([\w-]+)\]:", re.MULTILINE)
_TOKEN_RE = re.compile(r"\[\^([\w-]+)\]")
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)


def _strip_code(text: str) -> str:
    """Blank fenced code blocks while preserving line numbers."""
    return _FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def _at_line_start(text: str, idx: int) -> bool:
    j = idx - 1
    while j >= 0 and text[j] in " \t":
        j -= 1
    return j < 0 or text[j] == "\n"


def find_orphans(text: str) -> list[dict]:
    """Return one finding per orphaned footnote marker or definition."""
    scan = _strip_code(text)

    definitions: dict[str, int] = {}
    for m in _DEF_RE.finditer(scan):
        definitions.setdefault(m.group(1), _line_of(scan, m.start()))

    markers: dict[str, int] = {}
    for m in _TOKEN_RE.finditer(scan):
        end = m.end()
        # The ``[^x]`` that opens a definition (``[^x]:`` at line start) is not
        # an inline reference; skip it so a defined-and-referenced label is clean.
        if end < len(scan) and scan[end] == ":" and _at_line_start(scan, m.start()):
            continue
        markers.setdefault(m.group(1), _line_of(scan, m.start()))

    findings: list[dict] = []
    for label, line in markers.items():
        if label not in definitions:
            findings.append({"rule": "footnote-integrity", "kind": "orphan-marker",
                             "label": label, "line": line})
    for label, line in definitions.items():
        if label not in markers:
            findings.append({"rule": "footnote-integrity", "kind": "orphan-definition",
                             "label": label, "line": line})
    findings.sort(key=lambda f: (f["line"], f["kind"], f["label"]))
    return findings


def lint_footnotes(path: Path) -> list[dict]:
    return find_orphans(load_markdown(path))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_footnotes.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_footnotes(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
