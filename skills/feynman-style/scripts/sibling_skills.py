"""Locate sibling skills and load their parsed catalogs.

The humanizer skill ships its 24-pattern "Signs of AI writing" catalog as
markdown documentation plus (optionally) a JSON file. This module returns
a normalised dict the AI-vocabulary linter consumes. If humanizer is not
installed, callers receive a SiblingNotFoundError; the AI-vocab linter
runs the Russell-specific overlay alone in that case.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


class SiblingNotFoundError(Exception):
    pass


def _skills_root() -> Path:
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    return home / ".claude" / "skills"


def _humanizer_root() -> Path:
    return _skills_root() / "humanizer"


def humanizer_available() -> bool:
    root = _humanizer_root()
    return root.is_dir() and (root / "SKILL.md").is_file()


def load_humanizer_catalog() -> dict:
    """Return a dict of {pattern_id: [phrases]} parsed from humanizer.

    Strategy:
    - Prefer humanizer/assets/patterns.json if present.
    - Fall back to parsing the bullet lists inside SKILL.md sections that
      enumerate patterns (em-dash overuse, magic adverbs, etc.).
    """
    if not humanizer_available():
        raise SiblingNotFoundError(f"humanizer not found at {_humanizer_root()}")
    root = _humanizer_root()

    patterns_json = root / "assets" / "patterns.json"
    if patterns_json.is_file():
        return json.loads(patterns_json.read_text(encoding="utf-8"))

    text = (root / "SKILL.md").read_text(encoding="utf-8")
    catalog: dict[str, list[str]] = {}
    section_re = re.compile(r"^### +(.+?)$", re.MULTILINE)
    matches = list(section_re.finditer(text))
    for i, m in enumerate(matches):
        heading = m.group(1).strip().lower().replace(" ", "_")
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        phrases: list[str] = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith(("- ", "* ")):
                phrases.append(line[2:].strip().strip("*_`"))
        if phrases:
            catalog[heading] = phrases
    if not catalog:
        catalog = {"_empty": []}
    return catalog
