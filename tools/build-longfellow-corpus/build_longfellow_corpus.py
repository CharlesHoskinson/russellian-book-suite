"""Build a study corpus of public-domain Longfellow stanzas with verified snippets.

Two responsibilities:

1. Pure, stdlib-only: poetry-aware segmentation (``segment_stanzas``) and index
   assembly (``build_index``). Offline and CI-testable.

2. Network: ``fetch_work_markdown(url)`` reaches scrapling-fetch by subprocess (the
   suite's network boundary, per scrapling-fetch/SKILL.md). Run-once by the
   orchestrator; not exercised in CI.

The committed artifact is ``skills/russellian-style/assets/longfellow-corpus/index.json``.
Tests assert the schema of that artifact; the network step is performed manually.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


COPYRIGHT_POLICY = (
    "Public-domain (US) source. Short verified verse snippets are stored for anchor "
    "use; cite the source URL and locator (canto, line group) in any report. "
    "Borrow cadence and image-logic only — never meter, rhyme, archaism, or sentiment."
)


def segment_stanzas(markdown: str, min_lines: int = 2) -> list[str]:
    """Split verse markdown into stanzas, preserving line breaks within each.

    A stanza is a blank-line-separated block of at least ``min_lines`` non-empty lines
    that does not begin with a markdown heading. Whitespace inside each line is
    preserved so meter is visible.
    """
    stanzas: list[str] = []
    for block in re.split(r"\n\s*\n", markdown):
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < min_lines:
            continue
        if lines[0].lstrip().startswith("#"):
            continue
        stanzas.append("\n".join(l.strip() for l in lines))
    return stanzas


def build_index(sources: dict, anchors: list, version: str = "0.1.0") -> dict:
    """Assemble the index.json content from verified sources and curated anchors."""
    return {
        "version": version,
        "donor": "Henry Wadsworth Longfellow (public domain)",
        "copyright_policy": COPYRIGHT_POLICY,
        "sources": sources,
        "anchors": anchors,
    }


# --- Network entry point (run-once by orchestrator; not part of CI) ----------------

def fetch_work_markdown(url: str, *,
                        scrapling_root: str | None = None,
                        scrapling_python: str | None = None) -> str:
    """Fetch a Gutenberg work through scrapling-fetch and return clean markdown.

    Requires scrapling-fetch installed in a venv. The orchestrator passes either both
    arguments or sets env vars ``SCRAPLING_FETCH_ROOT`` (the skill's directory) and
    ``SCRAPLING_FETCH_PYTHON`` (its venv python).
    """
    scrapling_root = scrapling_root or os.environ.get("SCRAPLING_FETCH_ROOT")
    scrapling_python = scrapling_python or os.environ.get("SCRAPLING_FETCH_PYTHON")
    if not scrapling_root or not scrapling_python:
        raise RuntimeError(
            "Provide scrapling_root / scrapling_python (or env vars "
            "SCRAPLING_FETCH_ROOT / SCRAPLING_FETCH_PYTHON)."
        )
    snippet = (
        "import sys; from scripts.fetch import fetch; "
        "from scripts.extract import html_to_markdown; "
        "page = fetch(sys.argv[1], mode='plain'); "
        "sys.stdout.write(html_to_markdown(page.html, sys.argv[1]))"
    )
    result = subprocess.run(
        [scrapling_python, "-c", snippet, url],
        cwd=scrapling_root, check=True, capture_output=True, text=True,
    )
    return result.stdout


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("fetch", "build"):
        print("usage: build_longfellow_corpus.py fetch <url> > work.md\n"
              "       build_longfellow_corpus.py build <sources.json> <anchors.json> <out.json>",
              file=sys.stderr)
        return 2
    if argv[1] == "fetch":
        sys.stdout.write(fetch_work_markdown(argv[2]))
        return 0
    sources = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    anchors = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
    idx = build_index(sources, anchors)
    Path(argv[4]).write_text(json.dumps(idx, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {argv[4]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
