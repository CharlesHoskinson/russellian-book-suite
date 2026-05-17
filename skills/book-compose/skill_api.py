"""
Public API surface of book-compose (IF-BC-1).

read_lens is a consumer-side contract for Phase 4.
Full drafting-pipeline integration lands in Phase 9.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

API_VERSION = (0, 1)

__all__ = [
    "LensContractViolation",
    "Lens",
    "read_lens",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LensContractViolation(Exception):
    """Raised when a lens file violates the stable section contract."""


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Lens:
    chapter_id: str
    generated_at: datetime
    source_run_id: str
    n_topics: int
    n_disputed: int
    n_concepts: int
    coverage_score: float
    topics_md: str
    disputed_md: str
    concepts_md: str
    coverage_md: str


# ---------------------------------------------------------------------------
# Lens file contract
#
# Path: <workspace_root>/syntopical/lenses/<chapter_id>.md
#
# Format:
#   ---
#   <YAML frontmatter>
#   ---
#   ## Topics
#   ...
#   ## Disputed Questions
#   ...
#   ## Concept Reconciliation
#   ...
#   ## Coverage
#   ...
#
# The four H2 sections MUST appear in the order above.  Any other order
# is a contract violation.
# ---------------------------------------------------------------------------

# Required H2 sections in the canonical order
_REQUIRED_SECTIONS = [
    "Topics",
    "Disputed Questions",
    "Concept Reconciliation",
    "Coverage",
]

_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body.  Returns (fm_dict, body)."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}, text
    fm_text = "".join(lines[1:end_idx])
    body = "".join(lines[end_idx + 1:])
    try:
        import yaml
        fm = yaml.safe_load(fm_text) or {}
    except Exception as exc:
        raise LensContractViolation(f"YAML frontmatter parse error: {exc}") from exc
    return fm, body


def _parse_sections(body: str) -> dict[str, str]:
    """Split body by the four canonical section H2 headers only.

    Content inside a section may itself contain H2 subheadings (e.g. the
    topic-map writes '## <node_id>' rows).  We therefore anchor only on the
    exact required section titles, not on every H2 in the document.
    """
    # Build a pattern that matches only the canonical headers.
    _required_set = {s.lower() for s in _REQUIRED_SECTIONS}
    matches = [m for m in _H2_RE.finditer(body)
               if m.group(1).strip().lower() in _required_set]
    if not matches:
        return {}
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[title] = body[start:end].strip()
    return sections


def _parse_datetime(value) -> datetime:
    """Parse an ISO 8601 datetime string or return it as-is if already datetime."""
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    # Handle trailing Z
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# IF-BC-1: read_lens
# ---------------------------------------------------------------------------

def read_lens(chapter_id: str, workspace_root: Path) -> Lens:
    """Read and parse the lens file for a chapter.

    Reads: <workspace_root>/syntopical/lenses/<chapter_id>.md

    Raises:
        FileNotFoundError — if the lens file does not exist.
        LensContractViolation — if sections are missing or out of order.
    """
    ws = Path(workspace_root)
    lens_path = ws / "syntopical" / "lenses" / f"{chapter_id}.md"

    if not lens_path.exists():
        raise FileNotFoundError(
            f"no lens file for chapter {chapter_id!r}; expected {lens_path}"
        )

    text = lens_path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)
    sections = _parse_sections(body)

    # Validate section presence
    missing = [s for s in _REQUIRED_SECTIONS if s not in sections]
    if missing:
        raise LensContractViolation(
            f"lens for {chapter_id!r} is missing required sections: {missing}"
        )

    # Validate section order
    present_ordered = [s for s in _REQUIRED_SECTIONS if s in sections]
    actual_order = [m.group(1).strip() for m in _H2_RE.finditer(body)
                    if m.group(1).strip() in _REQUIRED_SECTIONS]
    if actual_order != present_ordered:
        raise LensContractViolation(
            f"lens for {chapter_id!r} has sections in unexpected order: "
            f"{actual_order!r}; expected {present_ordered!r}"
        )

    return Lens(
        chapter_id=chapter_id,
        generated_at=_parse_datetime(fm.get("generated_at") or "1970-01-01T00:00:00Z"),
        source_run_id=str(fm.get("source_run_id") or ""),
        n_topics=int(fm.get("n_topics") or 0),
        n_disputed=int(fm.get("n_disputed") or 0),
        n_concepts=int(fm.get("n_concepts") or 0),
        coverage_score=float(fm.get("coverage_score") or 0.0),
        topics_md=sections["Topics"],
        disputed_md=sections["Disputed Questions"],
        concepts_md=sections["Concept Reconciliation"],
        coverage_md=sections["Coverage"],
    )
