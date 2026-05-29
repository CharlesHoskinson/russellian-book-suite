"""Run SPARQL competency queries against the workspace dataset."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from rdflib import Dataset

from .workspace import WorkspaceLayout

_ASSETS_ROOT = Path(__file__).resolve().parent.parent / "assets"

QUERY_CLASSES = ("coverage", "consistency", "defeasible")

# When False, defeasible query fires are recorded as warnings but never escalate
# to failure. When True, severity=critical defeasible fires hard-gate the run.
# Promoted to True after the bermuda Phase 4 run validated no false positives
# on a clean ledger (commit history in bermuda/fix-the-book branch).
BLOCKING_DEFEASIBLE = True


def discover_queries(assets_root: Path) -> list[tuple[str, str, Path]]:
    """Returns (class, name, path) for every .rq under assets/queries/."""
    base = assets_root / "queries"
    out: list[tuple[str, str, Path]] = []
    for cls in QUERY_CLASSES:
        cls_dir = base / cls
        if not cls_dir.exists():
            continue
        for f in sorted(cls_dir.glob("*.rq")):
            out.append((cls, f.stem, f))
    # Back-compat: flat .rq files at the top of queries/.
    for f in sorted(base.glob("*.rq")):
        out.append(("coverage", f.stem, f))
    return out


def _load_dataset(layout: WorkspaceLayout) -> Dataset:
    ds = Dataset(default_union=True)
    if layout.dataset.exists() and layout.dataset.stat().st_size > 0:
        ds.parse(layout.dataset, format="trig")
    return ds


def _load_defeasible_meta(assets_root: Path) -> dict:
    """Return the parsed _meta.yaml for defeasible queries, or {} if absent."""
    meta_path = assets_root / "queries" / "defeasible" / "_meta.yaml"
    if not meta_path.exists():
        return {}
    return yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}


def run_competency_queries(layout: WorkspaceLayout) -> dict:
    """Execute all competency queries and return results.

    Return shape
    ------------
    A dict with one key per query name (list of row tuples) plus a
    ``"warnings"`` key holding a list of defeasible-fire dicts::

        {
            "unsupported_claims": [...],
            "rebuttal-presence": [...],   # still present for back-compat
            ...
            "warnings": [
                {"query": "rebuttal-presence", "severity": "critical", "bindings": [...]},
                ...
            ],
        }

    Defeasible fires are non-blocking by default (``BLOCKING_DEFEASIBLE = False``).
    When ``BLOCKING_DEFEASIBLE`` is ``True`` and a defeasible query with
    ``severity == "critical"`` returns rows, the function raises ``RuntimeError``.
    """
    ds = _load_dataset(layout)
    meta = _load_defeasible_meta(_ASSETS_ROOT)

    findings: dict[str, list[tuple]] = {}
    warnings: list[dict] = []
    hard_failures: list[dict] = []

    for cls, name, query_path in discover_queries(_ASSETS_ROOT):
        rows = [
            tuple(str(v) if v is not None else "" for v in row)
            for row in ds.query(query_path.read_text(encoding="utf-8"))
        ]
        findings[name] = rows

        if cls == "defeasible" and rows:
            severity = (meta.get(name) or {}).get("severity", "minor")
            exc = (meta.get(name) or {}).get("exception_queries", [])
            if exc:
                raise NotImplementedError(
                    f"Defeasible query {name!r} declares exception_queries={exc} but the "
                    f"exception-evaluation mechanism is not yet implemented. Set exception_queries: [] "
                    f"or implement the loop in run_competency_queries.py."
                )
            entry = {"query": name, "severity": severity, "bindings": rows}
            warnings.append(entry)
            if BLOCKING_DEFEASIBLE and severity == "critical":
                hard_failures.append(entry)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = layout.graph_reports / f"competency-{timestamp}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Competency Query Report — {timestamp}\n"]
    for name, rows in findings.items():
        lines.append(f"## {name}\n")
        if rows:
            for row in rows:
                lines.append(f"- {row}")
        else:
            lines.append("_(no rows)_")
        lines.append("")
    if warnings:
        lines.append("## Defeasible Warnings\n")
        for w in warnings:
            lines.append(f"- [{w['severity']}] {w['query']}: {len(w['bindings'])} row(s)")
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    findings["warnings"] = warnings  # type: ignore[assignment]

    if hard_failures:
        names = ", ".join(f["query"] for f in hard_failures)
        raise RuntimeError(
            f"Defeasible queries with severity=critical fired: {names}"
        )

    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: run_competency_queries.py <workspace-dir>", file=sys.stderr)
        return 2
    layout = WorkspaceLayout(Path(argv[1]))
    try:
        findings = run_competency_queries(layout)
    except RuntimeError as e:
        # BLOCKING_DEFEASIBLE hard-gate fired. Surface a clean gate-failure
        # message and a distinct non-zero exit code instead of a raw traceback.
        print(f"GATE FAILED: {e}", file=sys.stderr)
        return 3
    for name, rows in findings.items():
        if name == "warnings":
            print(f"warnings: {len(rows)} defeasible fire(s)")
        else:
            print(f"{name}: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
