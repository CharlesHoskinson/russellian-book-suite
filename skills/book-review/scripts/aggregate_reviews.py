"""Aggregate per-persona review reports into chapters/drafts/<chapter>/persona-review.md."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .dispatch_review import parse_review_report, ReviewResult


@dataclass(frozen=True)
class AggregatedReview:
    chapter_id: str
    severity_counts: dict
    per_persona_verdicts: dict
    critical: list
    important: list
    minor: list
    report_path: Path


def _gather_reviews(workspace: Path, chapter_id: str) -> list[ReviewResult]:
    reviews_dir = Path(workspace) / "chapters" / "drafts" / chapter_id / "reviews"
    if not reviews_dir.is_dir():
        return []
    out: list[ReviewResult] = []
    for path in sorted(reviews_dir.glob("*.md")):
        try:
            out.append(parse_review_report(path))
        except (ValueError, KeyError):
            continue
    return out


def _dedup_findings(findings: list[tuple[str, str]]) -> list[dict]:
    """Collapse findings only on exact normalized equality.

    Bare substring containment is never used to drop a finding: a short generic
    finding must not swallow a longer, more-specific one. Exact (case/whitespace-
    insensitive) duplicates across personas are merged into a single entry whose
    persona attribution lists every persona that raised it, in encounter order.
    """
    out: list[dict] = []
    by_norm: dict[str, dict] = {}
    for persona_id, text in findings:
        norm = text.lower().strip()
        existing = by_norm.get(norm)
        if existing is None:
            entry = {"persona": persona_id, "_personas": [persona_id], "text": text}
            by_norm[norm] = entry
            out.append(entry)
        elif persona_id not in existing["_personas"]:
            existing["_personas"].append(persona_id)
            existing["persona"] = ", ".join(existing["_personas"])
    for entry in out:
        entry.pop("_personas", None)
    return out


def aggregate_reviews(workspace: Path, chapter_id: str) -> AggregatedReview:
    workspace = Path(workspace).resolve()
    reviews = _gather_reviews(workspace, chapter_id)

    crit_pairs = [(r.persona_id, f.text) for r in reviews for f in r.critical]
    imp_pairs = [(r.persona_id, f.text) for r in reviews for f in r.important]
    min_pairs = [(r.persona_id, f.text) for r in reviews for f in r.minor]

    critical = _dedup_findings(crit_pairs)
    important = _dedup_findings(imp_pairs)
    minor = _dedup_findings(min_pairs)

    # Gating counts are the RAW per-persona sums, never the deduplicated
    # display-list lengths. Dedup collapses cross-persona repeats for
    # presentation; using it for the gate would let a chapter that should
    # block (multiple personas flag the same critical issue) slip through.
    severity_counts = {
        "critical": len(crit_pairs),
        "important": len(imp_pairs),
        "minor": len(min_pairs),
    }

    per_persona = {r.persona_id: r.verdict for r in reviews}

    persona_breakdown_by_severity: dict[str, dict[str, int]] = {}
    for r in reviews:
        persona_breakdown_by_severity[r.persona_id] = {
            "critical": len(r.critical),
            "important": len(r.important),
            "minor": len(r.minor),
        }

    out_dir = workspace / "chapters" / "drafts" / chapter_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "persona-review.md"

    lines: list[str] = [
        f"# Persona Review - {chapter_id}",
        "",
        f"_Aggregated {datetime.now(timezone.utc).isoformat(timespec='seconds')}_",
        "",
        "## Severity counts",
        "",
        f"- Critical: {severity_counts['critical']}",
        f"- Important: {severity_counts['important']}",
        f"- Minor: {severity_counts['minor']}",
        "",
        "## Per-persona verdicts",
        "",
        "| Persona | Verdict | Critical | Important | Minor |",
        "|---|---|---|---|---|",
    ]
    for pid, verdict in sorted(per_persona.items()):
        breakdown = persona_breakdown_by_severity.get(pid, {})
        lines.append(
            f"| {pid} | {verdict} | "
            f"{breakdown.get('critical', 0)} | "
            f"{breakdown.get('important', 0)} | "
            f"{breakdown.get('minor', 0)} |"
        )
    lines += ["", "## Aggregated critical findings", ""]
    for f in critical:
        lines.append(f"- ({f['persona']}) {f['text']}")
    if not critical:
        lines.append("_(none)_")
    lines += ["", "## Aggregated important findings", ""]
    for f in important:
        lines.append(f"- ({f['persona']}) {f['text']}")
    if not important:
        lines.append("_(none)_")
    lines += ["", "## Aggregated minor findings", ""]
    for f in minor:
        lines.append(f"- ({f['persona']}) {f['text']}")
    if not minor:
        lines.append("_(none)_")

    out_path.write_text("\n".join(lines), encoding="utf-8")

    return AggregatedReview(
        chapter_id=chapter_id,
        severity_counts=severity_counts,
        per_persona_verdicts=per_persona,
        critical=critical,
        important=important,
        minor=minor,
        report_path=out_path,
    )
