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


def _parse_line_range(text: str) -> Optional[tuple[int, int]]:
    """Return (start, end) line numbers from the first match in `text`, or None."""
    m = _LINE_RANGE_RE.search(text)
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else start
    return (start, end)


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


def cluster_findings(findings: list[Finding]) -> list[Cluster]:
    """Group findings whose line ranges are within _CLUSTER_GAP_LINES of each other.

    Findings without a line_range are dropped (cannot be located in the chapter).
    """
    located = [f for f in findings if f.line_range is not None]
    if not located:
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
    return clusters


_SEVERITY_ORDER = {"critical": 0, "important": 1, "minor": 2}


def render_instructions_markdown(chapter_id: str, clusters: list[Cluster]) -> str:
    """Emit the revision-instructions.md for the reviser.

    Only Critical and Important clusters are forwarded (Minor are reported by
    cycle_report but not revised). Clusters sorted by severity DESC then by
    distinct-persona count DESC then by line_start ASC.
    """
    eligible = [c for c in clusters if c.severity_tier in ("critical", "important")]
    if not eligible:
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
    args = parser.parse_args(argv)

    findings = parse_panel_summary(args.panel_summary)
    clusters = cluster_findings(findings)
    md = render_instructions_markdown(args.chapter_id, clusters)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")

    eligible = [c for c in clusters if c.severity_tier in ("critical", "important")]
    print(f"[synthesize_findings] {len(findings)} findings -> {len(clusters)} clusters "
          f"({len(eligible)} eligible) -> {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
