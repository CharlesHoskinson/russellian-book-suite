"""Load Outcomes exemplars from book-review/references/outcomes/<exemplar>/ and
render a per-persona few-shot snippet for injection into persona prompts.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from .placeholder import is_placeholder as _is_placeholder
from .sibling_skills import load_book_review_module


@dataclass(frozen=True)
class ExemplarFinding:
    persona_id: str
    severity: str  # "critical" | "important" | "minor"
    text: str
    source_path: Path


def _parse(path: Path) -> list[ExemplarFinding]:
    dr = load_book_review_module("dispatch_review")
    result = dr.parse_review_report(path)
    out: list[ExemplarFinding] = []
    for f in result.critical:
        if _is_placeholder(f.text):
            continue
        out.append(ExemplarFinding(result.persona_id, "critical", f.text, path))
    for f in result.important:
        if _is_placeholder(f.text):
            continue
        out.append(ExemplarFinding(result.persona_id, "important", f.text, path))
    for f in result.minor:
        if _is_placeholder(f.text):
            continue
        out.append(ExemplarFinding(result.persona_id, "minor", f.text, path))
    return out


def load_exemplars(paths: list[Path]) -> dict[str, list[ExemplarFinding]]:
    """Return persona_id -> list of findings across all given exemplar directories."""
    by_persona: dict[str, list[ExemplarFinding]] = {}
    for base in paths:
        base = Path(base)
        if not base.is_dir():
            continue
        for path in sorted(base.glob("*.md")):
            if path.stem in {"README", "curation-notes"}:
                continue
            try:
                for f in _parse(path):
                    by_persona.setdefault(f.persona_id, []).append(f)
            except (ValueError, KeyError, FileNotFoundError):
                continue
    return by_persona


def pick_findings(
    exemplars: dict[str, list[ExemplarFinding]],
    per_persona: int,
    seed: int = 42,
) -> dict[str, list[ExemplarFinding]]:
    """Deterministically select up to per_persona findings per persona."""
    rng = random.Random(seed)
    picked: dict[str, list[ExemplarFinding]] = {}
    for persona_id, findings in exemplars.items():
        if not findings:
            continue
        ordered = sorted(findings, key=lambda f: (f.severity, f.text))
        rng.shuffle(ordered)
        picked[persona_id] = ordered[:per_persona]
    return picked


def render_few_shot(persona_id: str, picked: dict[str, list[ExemplarFinding]]) -> str:
    """Render the chosen findings as a markdown snippet for prompt injection."""
    findings = picked.get(persona_id, [])
    if not findings:
        return ""
    lines = ["## Recent findings from this rubric", ""]
    for f in findings:
        lines.append(f"- _({f.severity})_ {f.text}")
    return "\n".join(lines)
