"""Stage 3 of the review-revise-validate cycle.

Pure-Python clustering of panel findings into revision instructions for
the reviser persona. Reads a panel-summary markdown (from book-review's
aggregate_reviews); writes a revision-instructions markdown.

Satisfies REQ-REVISE-003 (before/after counts are emitted by cycle_report;
this module's contribution is the synthesis step's findings-to-clusters
transformation).
"""
from __future__ import annotations

import re
from typing import Optional

_LINE_RANGE_RE = re.compile(r"lines?\s+(\d+)(?:[-–](\d+))?", re.IGNORECASE)

# Matches quoted snippets using straight or curly double-quote pairs.
# Requires at least 8 chars to avoid false positives on short tokens.
_QUOTED_SNIPPET_RE = re.compile(r'["“”]([^"“”]{8,})["“”]')


def _parse_line_range(text: str) -> Optional[tuple[int, int]]:
    """Return (start, end) line numbers from the first match in `text`, or None."""
    m = _LINE_RANGE_RE.search(text)
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else start
    return (start, end)


def _extract_first_quoted_snippet(text: str) -> Optional[str]:
    """Return the first quoted substring in text that's at least 8 chars long."""
    m = _QUOTED_SNIPPET_RE.search(text)
    return m.group(1) if m else None


def _locate_snippet_in_chapter(snippet: str, chapter_lines: list[str]) -> Optional[tuple[int, int]]:
    """Return (start_line, end_line) where snippet appears in chapter_lines, or None.

    Lines are 1-indexed. The match is verbatim substring within a single line
    OR falls back to a 40-char prefix match if exact fails.
    """
    if not snippet:
        return None
    # Try exact match within a single line first
    for i, line in enumerate(chapter_lines, start=1):
        if snippet in line:
            return (i, i)
    # Try 40-char prefix anchor (handles minor whitespace/punctuation drift)
    prefix = snippet[:40].strip()
    if len(prefix) < 10:
        return None
    for i, line in enumerate(chapter_lines, start=1):
        if prefix in line:
            return (i, i)
    return None


from dataclasses import dataclass, field


_THEME_PATTERNS: dict[str, list[str]] = {
    "listicle": [r"listicle", r"rests on \w+ premises", r"consists of \w+ components"],
    "mechanical-parallel": [r"mechanical parallel structure", r"mechanical (?:thesis )?enumeration", r"mechanical anaphora"],
    "formulaic-template": [r"formulaic", r"template, not writing"],
    "em-dash-overuse": [r"em[- ]dash(?:es)? overuse", r"em[- ]dash(?:es)? where a comma"],
    "hedging": [r"working estimate", r"awaits .* publication", r"precise figures await", r"hedging chain"],
    "lead-buried": [r"lead is buried", r"hook (?:doesn't|does not) arrive", r"buried lede"],
    "voice-slip": [r"voice slip", r"abandons the chapter's register"],
    "jargon-density": [r"jargon density", r"acronyms? .* without definition"],
}


def _tag_themes(text: str) -> set[str]:
    """Return the set of theme tags that match `text` (case-insensitive)."""
    tags: set[str] = set()
    lower = text.lower()
    for theme, patterns in _THEME_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower):
                tags.add(theme)
                break
    return tags


@dataclass
class Finding:
    """One severity-tagged finding extracted from a persona review."""
    persona_id: str
    severity: str  # "critical" | "important" | "minor"
    text: str
    line_range: Optional[tuple[int, int]] = None
    themes: set[str] = field(default_factory=set)


@dataclass
class Cluster:
    """Group of findings on overlapping/adjacent lines."""
    cluster_id: str
    line_start: int
    line_end: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def distinct_personas(self) -> set[str]:
        return {f.persona_id for f in self.findings}

    @property
    def severity_tier(self) -> str:
        """max severity in cluster — critical > important > minor."""
        if any(f.severity == "critical" for f in self.findings):
            return "critical"
        if any(f.severity == "important" for f in self.findings):
            return "important"
        return "minor"

    @property
    def theme_tags(self) -> set[str]:
        tags: set[str] = set()
        for f in self.findings:
            tags |= f.themes
        return tags


from pathlib import Path


_CLUSTER_GAP_LINES = 5  # findings within this many lines merge into one cluster
_PANEL_SECTION_RE = re.compile(
    r"##\s+Aggregated\s+(critical|important|minor)\s+findings\s*\n(.*?)(?=\n##\s+|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_FINDING_BULLET_RE = re.compile(r"^\s*-\s+([a-z0-9_\-]+):\s+(.+?)\s*$", re.MULTILINE)


def parse_panel_summary(path: Path) -> list[Finding]:
    """Extract a flat list of Finding objects from an aggregator's panel-summary.md."""
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    for sect_match in _PANEL_SECTION_RE.finditer(text):
        severity = sect_match.group(1).lower()
        body = sect_match.group(2)
        if "_(none)_" in body:
            continue
        for bullet in _FINDING_BULLET_RE.finditer(body):
            persona_id = bullet.group(1)
            finding_text = bullet.group(2)
            line_range = _parse_line_range(finding_text)
            themes = _tag_themes(finding_text)
            findings.append(Finding(
                persona_id=persona_id,
                severity=severity,
                text=finding_text,
                line_range=line_range,
                themes=themes,
            ))
    return findings


def cluster_findings(
    findings: list[Finding],
    chapter_text: Optional[str] = None,
) -> tuple[list[Cluster], list[Finding]] | list[Cluster]:
    """Group findings whose line ranges are within _CLUSTER_GAP_LINES of each other.

    When chapter_text is provided:
      - Findings without a line_range get snippet-anchoring attempted via
        _locate_snippet_in_chapter(_extract_first_quoted_snippet(finding.text), ...).
        If a location is found the finding's line_range is set in-place.
      - Critical/Important findings that remain unanchored are returned as the
        second element of the tuple (list[Finding]).
      - Minor unanchored findings are silently dropped.
    Returns a tuple (clusters, unanchored) when chapter_text is provided.

    When chapter_text is None (default), behavior is unchanged from the
    original: unanchored findings are dropped and only clusters is returned
    as a plain list (backward-compatible).
    """
    chapter_lines: Optional[list[str]] = None
    if chapter_text is not None:
        chapter_lines = chapter_text.splitlines()

    # Attempt snippet anchoring when chapter text is available
    unanchored: list[Finding] = []
    for f in findings:
        if f.line_range is None and chapter_lines is not None:
            snippet = _extract_first_quoted_snippet(f.text)
            if snippet:
                loc = _locate_snippet_in_chapter(snippet, chapter_lines)
                if loc is not None:
                    f.line_range = loc
            # Still unanchored — route critical/important to unanchored list
            if f.line_range is None and f.severity in ("critical", "important"):
                unanchored.append(f)

    located = [f for f in findings if f.line_range is not None]
    if not located:
        if chapter_text is not None:
            return ([], unanchored)
        return []
    located.sort(key=lambda f: f.line_range[0])

    clusters: list[Cluster] = []
    cluster_idx = 0
    current = Cluster(
        cluster_id=f"C{cluster_idx + 1:02d}",
        line_start=located[0].line_range[0],
        line_end=located[0].line_range[1],
        findings=[located[0]],
    )

    for f in located[1:]:
        if f.line_range[0] <= current.line_end + _CLUSTER_GAP_LINES:
            current.findings.append(f)
            current.line_end = max(current.line_end, f.line_range[1])
        else:
            clusters.append(current)
            cluster_idx += 1
            current = Cluster(
                cluster_id=f"C{cluster_idx + 1:02d}",
                line_start=f.line_range[0],
                line_end=f.line_range[1],
                findings=[f],
            )
    clusters.append(current)

    if chapter_text is not None:
        return (clusters, unanchored)
    return clusters


_SEVERITY_ORDER = {"critical": 0, "important": 1, "minor": 2}


def render_instructions_markdown(
    chapter_id: str,
    clusters: list[Cluster],
    unanchored: Optional[list[Finding]] = None,
) -> str:
    """Emit the revision-instructions.md for the reviser.

    Only Critical and Important clusters are forwarded (Minor are reported by
    cycle_report but not revised). Clusters sorted by severity DESC then by
    distinct-persona count DESC then by line_start ASC.

    When unanchored is provided (non-empty), a '## Unanchored findings' section
    is appended listing Critical/Important findings that could not be located.
    """
    if unanchored is None:
        unanchored = []

    eligible = [c for c in clusters if c.severity_tier in ("critical", "important")]
    if not eligible and not unanchored:
        return (
            f"# Revision instructions for {chapter_id}\n\n"
            f"_(no clusters eligible for revision — Critical and Important counts both zero)_\n"
        )

    eligible.sort(key=lambda c: (
        _SEVERITY_ORDER[c.severity_tier],
        -len(c.distinct_personas),
        c.line_start,
    ))

    lines: list[str] = [f"# Revision instructions for {chapter_id}", ""]
    for c in eligible:
        personas = ", ".join(sorted(c.distinct_personas))
        themes = ", ".join(sorted(c.theme_tags)) if c.theme_tags else "(no theme tag)"
        lines.append(f"## Cluster {c.cluster_id} ({c.severity_tier.title()}; "
                     f"{len(c.distinct_personas)} personas: {personas})")
        lines.append(f"Lines {c.line_start}-{c.line_end} — theme: {themes}")
        lines.append("")
        lines.append("Findings:")
        for f in c.findings:
            lines.append(f"- **{f.persona_id}** ({f.severity}): {f.text}")
        lines.append("")
        lines.append("Fix recipe: address the convergent feedback while preserving the author's voice.")
        lines.append("")

    # Emit unanchored section for Critical/Important findings with no locatable line range
    unanchored_eligible = [f for f in unanchored if f.severity in ("critical", "important")]
    if unanchored_eligible:
        lines.append("## Unanchored findings")
        lines.append("")
        lines.append(
            "The following Critical/Important findings could not be anchored to a specific "
            "line range in the chapter (no line reference or locatable quoted snippet). "
            "Address them as global prose concerns."
        )
        lines.append("")
        for f in unanchored_eligible:
            snippet_hint = _extract_first_quoted_snippet(f.text)
            hint_str = f' (snippet hint: "{snippet_hint}")' if snippet_hint else ""
            lines.append(f"- **{f.persona_id}** ({f.severity}){hint_str}: {f.text}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-summary", type=Path, required=True,
                        help="Path to the book-review aggregator's panel-summary.md")
    parser.add_argument("--chapter-id", type=str, required=True,
                        help="Chapter identifier for the output heading (e.g. ch-01)")
    parser.add_argument("--output", type=Path, required=True,
                        help="Where to write the revision-instructions.md")
    parser.add_argument("--chapter-md", type=Path, default=None,
                        help="Path to the chapter draft for snippet-anchoring unanchored findings")
    args = parser.parse_args(argv)

    findings = parse_panel_summary(args.panel_summary)

    chapter_text: Optional[str] = None
    if args.chapter_md is not None and args.chapter_md.exists():
        chapter_text = args.chapter_md.read_text(encoding="utf-8")

    result = cluster_findings(findings, chapter_text=chapter_text)
    if isinstance(result, tuple):
        clusters, unanchored = result
    else:
        clusters, unanchored = result, []

    md = render_instructions_markdown(args.chapter_id, clusters, unanchored)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")

    eligible = [c for c in clusters if c.severity_tier in ("critical", "important")]
    print(
        f"[synthesize_findings] {len(findings)} findings -> {len(clusters)} clusters "
        f"({len(eligible)} eligible) + {len(unanchored)} unanchored -> {args.output}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
