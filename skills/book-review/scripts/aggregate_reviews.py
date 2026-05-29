"""Aggregate per-persona review reports into chapters/drafts/<chapter>/persona-review.md."""
from __future__ import annotations

from dataclasses import dataclass, field
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
    failed_personas: list = field(default_factory=list)


def _gather_reviews(workspace: Path, chapter_id: str) -> tuple[list[ReviewResult], list[tuple[str, str]]]:
    """Parse every review report, returning (parsed, failures).

    failures is a list of (filename, reason) for reports that could not be
    parsed (missing frontmatter, schema-invalid). These are surfaced rather
    than silently dropped, so a broken/missing review does not invisibly
    shrink the gate's evidence base.
    """
    reviews_dir = Path(workspace) / "chapters" / "drafts" / chapter_id / "reviews"
    if not reviews_dir.is_dir():
        return [], []
    out: list[ReviewResult] = []
    failures: list[tuple[str, str]] = []
    for path in sorted(reviews_dir.glob("*.md")):
        try:
            out.append(parse_review_report(path))
        except (ValueError, KeyError) as exc:
            failures.append((path.name, str(exc)))
    return out, failures


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
    reviews, failed = _gather_reviews(workspace, chapter_id)

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
    #
    # The persona-supplied frontmatter *_count fields are authoritative when
    # they exceed the parsed body count: a brittle body parse that drops a
    # finding must not be allowed to undercount the gate. Take the larger of
    # (parsed body total, declared frontmatter total) per severity.
    def _declared_total(field: str) -> int:
        total = 0
        for r in reviews:
            val = r.raw_metadata.get(field)
            if isinstance(val, int) and val > 0:
                total += val
        return total

    severity_counts = {
        "critical": max(len(crit_pairs), _declared_total("critical_count")),
        "important": max(len(imp_pairs), _declared_total("important_count")),
        "minor": max(len(min_pairs), _declared_total("minor_count")),
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

    if failed:
        lines += ["", "## Failed personas", ""]
        lines.append(
            "_These reports could not be parsed and are NOT reflected in the "
            "counts above. The panel's evidence base is incomplete._"
        )
        lines.append("")
        for name, reason in failed:
            lines.append(f"- `{name}`: {reason}")

    out_path.write_text("\n".join(lines), encoding="utf-8")

    return AggregatedReview(
        chapter_id=chapter_id,
        severity_counts=severity_counts,
        per_persona_verdicts=per_persona,
        critical=critical,
        important=important,
        minor=minor,
        report_path=out_path,
        failed_personas=failed,
    )
