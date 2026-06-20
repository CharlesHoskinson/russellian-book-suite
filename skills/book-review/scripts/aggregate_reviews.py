"""Aggregate per-persona review reports into chapters/drafts/<chapter>/persona-review.md."""
from __future__ import annotations

import sys
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
    candidates = sorted(reviews_dir.glob("*.md"))
    for path in candidates:
        try:
            out.append(parse_review_report(path))
        except (ValueError, KeyError) as exc:
            reason = str(exc)
            failures.append((path.name, reason))
            print(f"[aggregate_reviews] WARNING: skipping {path.name}: {reason}", file=sys.stderr)

    if failures:
        print(
            f"[aggregate_reviews] {len(failures)} of {len(candidates)} candidate report(s) skipped.",
            file=sys.stderr,
        )

    if candidates and not out:
        raise ValueError(
            f"[aggregate_reviews] All {len(candidates)} candidate report(s) for "
            f"{chapter_id} were invalid — cannot produce aggregation. "
            f"Check that reports have valid YAML frontmatter."
        )

    return out, failures


def _gather_reviews_from_dir(reviews_dir: Path) -> tuple[list[ReviewResult], list[tuple[str, str]]]:
    """Read persona-review-*.md files from a flat directory, returning (parsed, failures).

    Mirrors _gather_reviews' behavior (warn on parse failures, surface them,
    fail if all invalid) but accepts any directory path rather than computing
    one from workspace + chapter_id.
    """
    reviews_dir = Path(reviews_dir)
    if not reviews_dir.is_dir():
        return [], []
    out: list[ReviewResult] = []
    failures: list[tuple[str, str]] = []
    candidates = sorted(reviews_dir.glob("*.md"))
    for path in candidates:
        try:
            out.append(parse_review_report(path))
        except (ValueError, KeyError) as exc:
            reason = str(exc)
            failures.append((path.name, reason))
            print(f"[aggregate_reviews] WARNING: skipping {path.name}: {reason}", file=sys.stderr)
    if failures:
        print(
            f"[aggregate_reviews] {len(failures)} of {len(candidates)} candidate report(s) skipped.",
            file=sys.stderr,
        )
    if candidates and not out:
        raise ValueError(
            f"[aggregate_reviews] All {len(candidates)} candidate report(s) in "
            f"{reviews_dir} were invalid."
        )
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


def _build_aggregated_review(reviews: list[ReviewResult], chapter_id: str) -> AggregatedReview:
    """Build an AggregatedReview from a list of ReviewResult objects.

    Does not perform any I/O. The returned AggregatedReview has report_path=Path('.')
    as a sentinel; callers should write the file themselves.
    """
    crit_pairs = [(r.persona_id, f.text) for r in reviews for f in r.critical]
    imp_pairs = [(r.persona_id, f.text) for r in reviews for f in r.important]
    min_pairs = [(r.persona_id, f.text) for r in reviews for f in r.minor]

    critical = _dedup_findings(crit_pairs)
    important = _dedup_findings(imp_pairs)
    minor = _dedup_findings(min_pairs)

    severity_counts = {
        "critical": len(critical),
        "important": len(important),
        "minor": len(minor),
    }
    per_persona = {r.persona_id: r.verdict for r in reviews}

    return AggregatedReview(
        chapter_id=chapter_id,
        severity_counts=severity_counts,
        per_persona_verdicts=per_persona,
        critical=critical,
        important=important,
        minor=minor,
        report_path=Path("."),
    )


def render_panel_summary_markdown(agg: AggregatedReview) -> str:
    """Render an AggregatedReview to a markdown string.

    The output uses bullet-list format for per-persona verdicts and findings so
    that the review-revise-validate orchestrator's synthesize_findings parser can
    extract structured data from the sections:

      ## Severity counts
      - Critical: N
      - Important: N
      - Minor: N

      ## Per-persona verdicts
      - <persona>: VERDICT

      ## Aggregated critical findings
      - <persona>: <text>

    (and likewise for important / minor findings).
    """
    lines: list[str] = [
        f"# Persona Review - {agg.chapter_id}",
        "",
        f"_Aggregated {datetime.now(timezone.utc).isoformat(timespec='seconds')}_",
        "",
        "## Severity counts",
        "",
        f"- Critical: {agg.severity_counts['critical']}",
        f"- Important: {agg.severity_counts['important']}",
        f"- Minor: {agg.severity_counts['minor']}",
        "",
        "## Per-persona verdicts",
        "",
    ]
    for pid, verdict in sorted(agg.per_persona_verdicts.items()):
        lines.append(f"- {pid}: {verdict}")
    if not agg.per_persona_verdicts:
        lines.append("_(none)_")

    lines += ["", "## Aggregated critical findings", ""]
    for f in agg.critical:
        lines.append(f"- {f['persona']}: {f['text']}")
    if not agg.critical:
        lines.append("_(none)_")

    lines += ["", "## Aggregated important findings", ""]
    for f in agg.important:
        lines.append(f"- {f['persona']}: {f['text']}")
    if not agg.important:
        lines.append("_(none)_")

    lines += ["", "## Aggregated minor findings", ""]
    for f in agg.minor:
        lines.append(f"- {f['persona']}: {f['text']}")
    if not agg.minor:
        lines.append("_(none)_")

    return "\n".join(lines)


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


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Legacy workspace mode: read from <workspace>/chapters/drafts/<chapter-id>/reviews/",
    )
    parser.add_argument(
        "--reviews-dir",
        type=Path,
        help="Direct-dir mode: read from this directory's *.md files",
    )
    parser.add_argument("--chapter-id", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        help="Where to write panel-summary.md (default in legacy mode: workspace path)",
    )
    args = parser.parse_args(argv)

    if not args.workspace and not args.reviews_dir:
        parser.error("either --workspace or --reviews-dir is required")
    if args.workspace and args.reviews_dir:
        parser.error("--workspace and --reviews-dir are mutually exclusive")

    if args.reviews_dir:
        # Direct-dir mode: read review files in args.reviews_dir
        reviews, _failed = _gather_reviews_from_dir(args.reviews_dir)
        if not reviews:
            print(
                f"[aggregate_reviews] no reviews found in {args.reviews_dir}",
                file=sys.stderr,
            )
            return 1
        agg = _build_aggregated_review(reviews, args.chapter_id)
        if args.output is None:
            parser.error("--output is required when using --reviews-dir")
        output_path = args.output
    else:
        # Legacy workspace mode
        reviews, _failed = _gather_reviews(args.workspace, args.chapter_id)
        if not reviews:
            print(
                f"[aggregate_reviews] no reviews under "
                f"{args.workspace}/chapters/drafts/{args.chapter_id}/reviews/",
                file=sys.stderr,
            )
            return 1
        agg = _build_aggregated_review(reviews, args.chapter_id)
        output_path = args.output or (
            args.workspace / "chapters" / "drafts" / args.chapter_id / "persona-review.md"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    md = render_panel_summary_markdown(agg)
    output_path.write_text(md, encoding="utf-8")
    print(f"[aggregate_reviews] wrote {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
