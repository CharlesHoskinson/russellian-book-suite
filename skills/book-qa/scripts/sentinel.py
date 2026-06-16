"""Stage-3 aggregator.

Rolls up Stage-1 ``defects.json`` (mechanical D1-D8 from
``lint_artifact.py``) with Stage-2 per-chapter ticket JSON files
(``qa/chapter-tickets/ch-NN.json``) into a single master report at
``<workspace>/qa/sentinel.json``.

Hard-fail rules (release blocked):

* Any critical D1-D8 mechanical defect or critical D9-D13 reasoning defect.
* Any C2 (cross-references) or C13 (closing strength) ticket from Stage 2.
* Any Stage-2 ticket with severity ``critical``.

Everything else is soft-gate: surfaced but not blocking.

CLI:
    python -m scripts.sentinel <workspace>

Exit code 1 if the hard-fail set is non-empty, 0 otherwise.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

HARD_FAIL_CHECKS = {"C2", "C13"}
HARD_FAIL_D_CLASSES = {
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8",
    "D9", "D10", "D11", "D13",
}


@dataclass
class Ticket:
    """Unified ticket shape across Stage 1 and Stage 2."""

    ticket_id: str
    source: str        # "lint" or "chapter-qa"
    chapter: str       # "ch-NN" or "doc" for whole-manuscript
    class_: str        # "D1".."D8" or "C1".."C15"
    severity: str      # "critical" | "important" | "minor"
    where: str
    detail: str
    fix_hint: str = ""
    hard_fail: bool = False


@dataclass
class SentinelReport:
    """Master roll-up emitted to ``qa/sentinel.json``."""

    total: int
    hard_fail_count: int
    by_class: dict[str, int]
    by_chapter: dict[str, int]
    by_severity: dict[str, int]
    hard_fail_tickets: list[dict[str, Any]]
    soft_gate_tickets: list[dict[str, Any]]
    all_tickets: list[dict[str, Any]] = field(default_factory=list)


def _is_hard_fail(class_: str, severity: str) -> bool:
    """Apply the v5.1 hard-fail policy uniformly."""
    if class_ in HARD_FAIL_D_CLASSES and severity == "critical":
        return True
    if class_ in HARD_FAIL_CHECKS:
        return True
    if class_.startswith("C") and severity == "critical":
        return True
    return False


def _corrupt_input_ticket(path: Path, exc: Exception) -> "Ticket":
    """A synthetic hard-fail ticket for a malformed QA input file (4.2).

    Corruption in a QA input must block the gate — not crash the run, and not be
    silently skipped (which would pass a chapter whose findings were unreadable).
    """
    return Ticket(
        ticket_id=f"corrupt-{path.stem}",
        source="sentinel",
        chapter=path.stem,
        class_="C-CORRUPT",
        severity="critical",
        where=str(path),
        detail=f"malformed QA input JSON: {exc}",
        fix_hint="regenerate this QA artifact; it is not valid JSON",
        hard_fail=True,
    )


def _load_stage1(workspace: Path) -> list[Ticket]:
    """Pull D1-D8 defects from ``qa/defects.json`` produced by lint_artifact."""
    path = workspace / "qa" / "defects.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [_corrupt_input_ticket(path, e)]
    out: list[Ticket] = []
    for i, entry in enumerate(payload.get("defects", [])):
        cls = entry.get("class") or entry.get("class_") or "D?"
        sev = entry.get("severity", "minor")
        out.append(Ticket(
            ticket_id=f"lint-{i:04d}",
            source="lint",
            chapter=entry.get("chapter", "doc"),
            class_=cls,
            severity=sev,
            where=entry.get("where", ""),
            detail=entry.get("detail", ""),
            fix_hint=entry.get("fix_hint", ""),
            hard_fail=_is_hard_fail(cls, sev),
        ))
    return out


def _load_stage2(workspace: Path) -> list[Ticket]:
    """Pull per-chapter Stage-2 tickets from ``qa/chapter-tickets/*.json``."""
    tix_dir = workspace / "qa" / "chapter-tickets"
    if not tix_dir.exists():
        return []
    out: list[Ticket] = []
    for path in sorted(tix_dir.glob("ch-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            out.append(_corrupt_input_ticket(path, e))
            continue
        chapter = payload.get("chapter", path.stem)
        for i, t in enumerate(payload.get("tickets", [])):
            cls = t.get("check", "C?")
            sev = t.get("severity", "minor")
            out.append(Ticket(
                ticket_id=f"{chapter}-{cls}-{i:03d}",
                source="chapter-qa",
                chapter=chapter,
                class_=cls,
                severity=sev,
                where=t.get("where", ""),
                detail=t.get("detail", ""),
                fix_hint=t.get("fix_hint", ""),
                hard_fail=_is_hard_fail(cls, sev),
            ))
    return out


def aggregate(workspace: Path, version: str | None = None) -> SentinelReport:
    """Merge Stage-1 and Stage-2 tickets into a single ``SentinelReport``.

    When *version* is supplied, ``propose_writeback`` is called after
    aggregation so that writeback artefacts land alongside QA outputs.
    """
    tickets = _load_stage1(workspace) + _load_stage2(workspace)
    by_class: dict[str, int] = {}
    by_chapter: dict[str, int] = {}
    by_severity: dict[str, int] = {"critical": 0, "important": 0, "minor": 0}
    hard, soft = [], []
    for t in tickets:
        by_class[t.class_] = by_class.get(t.class_, 0) + 1
        by_chapter[t.chapter] = by_chapter.get(t.chapter, 0) + 1
        by_severity[t.severity] = by_severity.get(t.severity, 0) + 1
        (hard if t.hard_fail else soft).append(_serialise(t))
    report = SentinelReport(
        total=len(tickets),
        hard_fail_count=len(hard),
        by_class=by_class,
        by_chapter=by_chapter,
        by_severity=by_severity,
        hard_fail_tickets=hard,
        soft_gate_tickets=soft,
        all_tickets=[_serialise(t) for t in tickets],
    )
    if version is not None:
        try:
            from .propose_writeback import propose_writeback  # noqa: PLC0415
            propose_writeback(workspace, version=version)
        except Exception as exc:  # noqa: BLE001
            print(f"[sentinel] propose_writeback failed (non-fatal): {exc}", file=sys.stderr)
    return report


def _serialise(t: Ticket) -> dict[str, Any]:
    """Rename ``class_`` -> ``class`` for JSON output (Python keyword)."""
    d = asdict(t)
    d["class"] = d.pop("class_")
    return d


def write_report(workspace: Path, report: SentinelReport) -> Path:
    """Persist the report to ``<workspace>/qa/sentinel.json`` and return its path."""
    out_dir = workspace / "qa"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "sentinel.json"
    path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    return path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: sentinel.py <workspace>", file=sys.stderr)
        return 2
    workspace = Path(argv[1]).resolve()
    report = aggregate(workspace)
    path = write_report(workspace, report)
    print(f"Sentinel report: {path}")
    print(f"  total tickets   : {report.total}")
    print(f"  hard-fail set   : {report.hard_fail_count}")
    print(f"  severity        : critical={report.by_severity.get('critical', 0)}"
          f"  important={report.by_severity.get('important', 0)}"
          f"  minor={report.by_severity.get('minor', 0)}")
    if report.by_class:
        cls_summary = ", ".join(f"{k}={v}" for k, v in sorted(report.by_class.items()))
        print(f"  by class        : {cls_summary}")
    if report.by_chapter:
        ch_summary = ", ".join(f"{k}={v}" for k, v in sorted(report.by_chapter.items()))
        print(f"  by chapter      : {ch_summary}")
    return 1 if report.hard_fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
