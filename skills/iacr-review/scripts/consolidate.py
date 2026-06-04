"""Consolidate N persona review files into one IACR review ledger.

Reads files matching `persona-*.md` from an input directory, parses each
persona's EC22-form review, and emits a ledger sorted by severity then
persona index. Detects cross-persona convergence (same paper section
appearing in multiple personas' findings).

Usage:
    python -m scripts.consolidate \\
        --reviews-dir paper/reviews \\
        --paper "EpochPoET" \\
        --version v0.3 \\
        --output paper/reviews/v0.3-review-ledger.md
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

SEVERITY_ORDER = ["strong-reject", "weak-reject", "borderline", "nit"]
RECOMMENDATION_NAMES = {
    1: "strong-reject",
    2: "weak-reject",
    3: "borderline",
    4: "accept",
    5: "strong-accept",
}

# Matches sections like "## C. Novelty, methodology, technical correctness".
SECTION_RE = re.compile(r"^##\s+([A-I])\.\s+(.+)$", re.MULTILINE)
# Matches subsection headers like "### Q3. Technical flaws".
SUBSECTION_RE = re.compile(r"^###\s+(Q\d)\.\s+(.+)$", re.MULTILINE)
# Matches `- [x] N <label>` selection lines.
CHECKBOX_RE = re.compile(r"^-\s*\[\s*[xX]\s*\]\s*(\d)\s+(.+)$", re.MULTILINE)
# Matches section/line refs like "section 4.2", "line 42", "page 17".
LOCATION_RE = re.compile(
    r"(section\s+[0-9]+(?:\.[0-9]+)*|line\s+[0-9]+|page\s+[0-9]+|"
    r"theorem\s+[0-9]+|lemma\s+[0-9]+|figure\s+[0-9]+)",
    re.IGNORECASE,
)


@dataclass
class Finding:
    finding_id: str = ""
    persona: str = ""
    persona_index: int = 99
    severity: str = "borderline"
    category: str = ""
    location: str = ""
    claim: str = ""
    evidence: str = ""
    suggested_fix: str = ""


@dataclass
class PersonaReview:
    path: Path
    persona_slug: str
    persona_index: int
    recommendation: int = 0
    confidence: int = 0
    findings: list[Finding] = field(default_factory=list)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_checkbox(text: str, after: str) -> int:
    """Return the integer value of the first ticked checkbox after `after`."""
    idx = text.find(after)
    if idx < 0:
        return 0
    window = text[idx : idx + 500]
    match = CHECKBOX_RE.search(window)
    return int(match.group(1)) if match else 0


def _split_sections(text: str) -> dict[str, str]:
    """Return mapping {section_letter: section_body}."""
    sections: dict[str, str] = {}
    matches = list(SECTION_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[m.group(1)] = text[start:end]
    return sections


def _severity_for_section(letter: str, recommendation: int) -> str:
    """Map a section letter and the persona's recommendation to a finding severity."""
    if recommendation == 1:
        return "strong-reject"
    if recommendation == 2:
        return "weak-reject"
    if letter == "E":
        return "nit"
    return "borderline"


def parse_review(path: Path) -> PersonaReview:
    text = _read(path)
    stem = path.stem  # persona-03-concrete-security
    parts = stem.split("-", 2)
    persona_index = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 99
    persona_slug = parts[2] if len(parts) >= 3 else stem

    recommendation = _extract_checkbox(text, "## H. Recommendation")
    confidence = _extract_checkbox(text, "## G. Confidence")

    sections = _split_sections(text)
    findings: list[Finding] = []
    counter = 0
    for letter in ("C", "D", "E"):
        body = sections.get(letter, "")
        if not body.strip():
            continue
        for sub in SUBSECTION_RE.finditer(body):
            sub_start = sub.end()
            next_sub = SUBSECTION_RE.search(body, sub_start)
            sub_end = next_sub.start() if next_sub else len(body)
            sub_body = body[sub_start:sub_end].strip()
            if not sub_body or sub_body.startswith("<"):
                continue
            loc_match = LOCATION_RE.search(sub_body)
            location = loc_match.group(0) if loc_match else "(no location cited)"
            claim = sub_body.splitlines()[0].strip().lstrip("-").strip()
            if len(claim) > 240:
                claim = claim[:237] + "..."
            counter += 1
            findings.append(
                Finding(
                    finding_id=f"F-{persona_index:02d}-{counter:02d}",
                    persona=persona_slug,
                    persona_index=persona_index,
                    severity=_severity_for_section(letter, recommendation),
                    category=f"{letter}/{sub.group(1)}",
                    location=location,
                    claim=claim,
                    evidence=sub_body[:400].replace("\n", " ").strip(),
                    suggested_fix="(see persona review)",
                )
            )
    return PersonaReview(
        path=path,
        persona_slug=persona_slug,
        persona_index=persona_index,
        recommendation=recommendation,
        confidence=confidence,
        findings=findings,
    )


def _severity_rank(s: str) -> int:
    try:
        return SEVERITY_ORDER.index(s)
    except ValueError:
        return len(SEVERITY_ORDER)


def _convergence(reviews: list[PersonaReview]) -> list[tuple[str, list[str]]]:
    """Cluster findings by location across personas."""
    by_loc: dict[str, list[str]] = {}
    for r in reviews:
        for f in r.findings:
            loc = f.location.lower()
            if loc.startswith("(no"):
                continue
            by_loc.setdefault(loc, []).append(f.finding_id)
    return [(loc, ids) for loc, ids in by_loc.items() if len({i.split("-")[1] for i in ids}) >= 2]


def render_ledger(
    reviews: list[PersonaReview], paper: str, version: str, today: str
) -> str:
    distribution = {name: 0 for name in RECOMMENDATION_NAMES.values()}
    for r in reviews:
        if r.recommendation in RECOMMENDATION_NAMES:
            distribution[RECOMMENDATION_NAMES[r.recommendation]] += 1

    recs = [r.recommendation for r in reviews if r.recommendation]
    median_name = RECOMMENDATION_NAMES.get(int(statistics.median(recs)), "n/a") if recs else "n/a"
    weighted_pairs = [(r.recommendation, max(r.confidence, 1)) for r in reviews if r.recommendation]
    if weighted_pairs:
        num = sum(rec * conf for rec, conf in weighted_pairs)
        denom = sum(conf for _, conf in weighted_pairs)
        weighted_mean = round(num / denom, 2)
    else:
        weighted_mean = 0.0

    all_findings = [f for r in reviews for f in r.findings]
    all_findings.sort(key=lambda f: (_severity_rank(f.severity), f.persona_index, f.finding_id))

    convergence = _convergence(reviews)

    lines: list[str] = [
        f"# IACR Review Ledger - {paper} {version}",
        "",
        f"Date: {today}. Source rubric: EC22 (EUROCRYPT 2022).",
        "",
        "## Summary",
        "",
        f"- Personas reviewed: {len(reviews)}",
        "- Recommendation distribution: "
        + ", ".join(f"{k} {v}" for k, v in distribution.items()),
        f"- Median recommendation: {median_name}",
        f"- Confidence-weighted mean: {weighted_mean}",
        "",
        "## Findings",
        "",
        "| ID | Persona | Severity | Category | Location | Claim | Evidence | Suggested fix |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in all_findings:
        claim = f.claim.replace("|", "\\|")
        evidence = f.evidence.replace("|", "\\|")
        lines.append(
            f"| {f.finding_id} | {f.persona} | {f.severity} | {f.category} | "
            f"{f.location} | {claim} | {evidence} | {f.suggested_fix} |"
        )
    if not all_findings:
        lines.append("| - | - | - | - | - | (no findings parsed) | - | - |")

    lines += ["", "## Cross-persona patterns", ""]
    if convergence:
        for loc, ids in sorted(convergence):
            lines.append(f"- **{loc}** flagged by: {', '.join(sorted(ids))}")
    else:
        lines.append("_(no convergence detected)_")

    lines += ["", "## Deferred fixes", ""]
    lines.append(
        "_Nits when the paper has structural defects, or domain disputes outside "
        "the paper's claimed contribution. Curator must annotate._"
    )

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviews-dir", required=True, type=Path)
    parser.add_argument("--paper", default="paper")
    parser.add_argument("--version", default="v0.0")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    review_files = sorted(args.reviews_dir.glob("persona-*.md"))
    if not review_files:
        # Accept version-prefixed filenames too (e.g. v0.3-persona-01-foo.md).
        review_files = sorted(args.reviews_dir.glob("*persona-*.md"))
    if not review_files:
        print(f"no *persona-*.md files found in {args.reviews_dir}", file=sys.stderr)
        return 1

    reviews = [parse_review(p) for p in review_files]
    ledger = render_ledger(reviews, args.paper, args.version, date.today().isoformat())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(ledger, encoding="utf-8")

    distribution = {name: 0 for name in RECOMMENDATION_NAMES.values()}
    for r in reviews:
        if r.recommendation in RECOMMENDATION_NAMES:
            distribution[RECOMMENDATION_NAMES[r.recommendation]] += 1
    print(f"wrote {args.output}")
    print(f"personas: {len(reviews)}")
    print(f"distribution: {distribution}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
