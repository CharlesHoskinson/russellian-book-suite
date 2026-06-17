"""Run competency queries against the workspace (Cozo, REQ-KG-006).

The eight homoiconic booklogic EDN ports (``assets/kg-queries/<name>.edn``) are
compiled to CozoScript and run over a projection of the claim ledger into an
in-memory Cozo store. The legacy SPARQL ``.rq`` path was removed in P5.4a-2.

Each query returns the same shape — a list of row tuples (cells stringified) — so
the defeasible / BLOCKING gate is uniform. A query's class
(``coverage``/``consistency``/``defeasible``) and, for defeasible queries, its
``severity`` + ``exception_queries`` come from ``assets/kg-queries/_meta.yaml``
(the manifest that replaced the old ``queries/<class>/`` tree + its _meta.yaml).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .workspace import WorkspaceLayout

_ASSETS_ROOT = Path(__file__).resolve().parent.parent / "assets"
_SCHEMA_PATH = _ASSETS_ROOT / "kg-schema.edn"
_EDN_QUERIES_DIR = _ASSETS_ROOT / "kg-queries"

# When False, defeasible query fires are recorded as warnings but never escalate
# to failure. When True, severity=critical defeasible fires hard-gate the run.
BLOCKING_DEFEASIBLE = True


def _load_manifest() -> dict:
    """Per-query class/severity manifest (assets/kg-queries/_meta.yaml)."""
    path = _EDN_QUERIES_DIR / "_meta.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def discover_queries(assets_root: Path) -> list[tuple[str, str, Path]]:
    """Return (class, name, edn_path) for every ``kg-queries/<name>.edn``.

    The class comes from ``kg-queries/_meta.yaml`` (default ``coverage``); manifest
    helper files (``_meta.yaml`` etc., ``_``-prefixed) are skipped.
    """
    edn_dir = assets_root / "kg-queries"
    manifest = {}
    meta_path = edn_dir / "_meta.yaml"
    if meta_path.exists():
        manifest = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    out: list[tuple[str, str, Path]] = []
    for f in sorted(edn_dir.glob("*.edn")):
        if f.stem.startswith("_"):
            continue
        cls = (manifest.get(f.stem) or {}).get("class", "coverage")
        out.append((cls, f.stem, f))
    return out


def _rows_str(rows) -> list[tuple]:
    """Stringify cells (None -> "") so the per-query result shape is stable."""
    return [
        tuple(str(v) if v is not None else "" for v in row) for row in rows
    ]


def _run_queries(
    layout: WorkspaceLayout, queries: list[tuple[str, str, Path]]
) -> dict[str, list[tuple]]:
    """Run the EDN ports over a Cozo projection of the ledger.

    Builds one in-memory Cozo store from ``kg-schema.edn``, projects the claim
    ledger into it, then runs each ``<name>.edn`` through the EDN seam
    ``store.query_edn`` (compiled to CozoScript internally). Rows are stringified
    through :func:`_rows_str`.
    """
    from .cozo_store import CozoStore  # local: keep pycozo cost off import
    from .project_ledger_cozo import project_ledger

    store = CozoStore.in_memory(schema_path=_SCHEMA_PATH)
    project_ledger(layout, store)

    findings: dict[str, list[tuple]] = {}
    for _cls, name, edn_path in queries:
        findings[name] = _rows_str(store.query_edn(edn_path.read_text(encoding="utf-8")))
    return findings


def run_competency_queries(layout: WorkspaceLayout) -> dict:
    """Execute all competency queries and return results.

    Return shape: a dict with one key per query name (list of row tuples) plus a
    ``"warnings"`` key holding a list of defeasible-fire dicts. Defeasible fires are
    blocking by default (``BLOCKING_DEFEASIBLE = True``): a defeasible query with
    ``severity == "critical"`` that returns rows raises ``RuntimeError``.
    """
    manifest = _load_manifest()
    queries = discover_queries(_ASSETS_ROOT)
    per_query = _run_queries(layout, queries)

    findings: dict[str, list[tuple]] = {}
    warnings: list[dict] = []
    hard_failures: list[dict] = []

    for cls, name, _edn_path in queries:
        rows = per_query[name]
        findings[name] = rows

        if cls == "defeasible" and rows:
            severity = (manifest.get(name) or {}).get("severity", "minor")
            exc = (manifest.get(name) or {}).get("exception_queries", [])
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
