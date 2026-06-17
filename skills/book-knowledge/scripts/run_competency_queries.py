"""Run competency queries against the workspace.

Two backends produce the SAME competency fire/defect result (REQ-KG-006):

* ``rdflib`` (DEFAULT) — runs the eight SPARQL ``.rq`` queries over the
  workspace's RDF dataset (``graph/dataset.trig``). Unchanged behavior.
* ``cozo`` — runs the eight homoiconic booklogic EDN ports
  (``assets/kg-queries/<name>.edn``) compiled to CozoScript over a projection of
  the claim ledger into an in-memory Cozo store. Selected by ``KG_BACKEND=cozo``.

The backend is parallel-run, not a cutover: the RDF path stays the default and is
untouched unless the flag is set. Both paths return the identical result shape
(``{query_name: [row_tuple, ...], "warnings": [...]}``) so the BLOCKING_DEFEASIBLE
gate and every downstream consumer are backend-agnostic.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from rdflib import Dataset

from .workspace import WorkspaceLayout

_ASSETS_ROOT = Path(__file__).resolve().parent.parent / "assets"
_SCHEMA_PATH = _ASSETS_ROOT / "kg-schema.edn"
_EDN_QUERIES_DIR = _ASSETS_ROOT / "kg-queries"

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


def _rows_str(rows) -> list[tuple]:
    """Stringify cells the way the rdflib path does (None -> "").

    Both backends route their per-query rows through this so the result shape is
    identical: a list of tuples of strings, in the backend's natural row order.
    """
    return [
        tuple(str(v) if v is not None else "" for v in row) for row in rows
    ]


def _run_queries_rdflib(
    layout: WorkspaceLayout, queries: list[tuple[str, str, Path]]
) -> dict[str, list[tuple]]:
    """Run the eight SPARQL ``.rq`` queries over the RDF dataset (default path)."""
    ds = _load_dataset(layout)
    findings: dict[str, list[tuple]] = {}
    for _cls, name, query_path in queries:
        findings[name] = _rows_str(ds.query(query_path.read_text(encoding="utf-8")))
    return findings


def _run_queries_cozo(
    layout: WorkspaceLayout, queries: list[tuple[str, str, Path]]
) -> dict[str, list[tuple]]:
    """Run the eight EDN ports over a Cozo projection of the ledger.

    Builds one in-memory Cozo store from ``kg-schema.edn``, projects the claim
    ledger into it (the relational counterpart of the RDF emit), then for each
    query loads ``assets/kg-queries/<name>.edn`` — the file name is the SAME stem
    as the ``.rq`` query name :func:`discover_queries` yields — and runs it
    through the EDN seam ``store.query_edn``, which compiles to CozoScript
    internally. Rows are stringified through :func:`_rows_str` so the returned
    shape is identical to the rdflib path. The booklogic ``:find`` order matches
    the SPARQL ``SELECT`` order, so per-row cell order matches too.
    """
    # Local imports keep pycozo/edn off the default (rdflib) path's import cost.
    from .cozo_store import CozoStore
    from .project_ledger_cozo import project_ledger

    store = CozoStore.in_memory(schema_path=_SCHEMA_PATH)
    project_ledger(layout, store)

    findings: dict[str, list[tuple]] = {}
    for _cls, name, _query_path in queries:
        edn = (_EDN_QUERIES_DIR / f"{name}.edn").read_text(encoding="utf-8")
        findings[name] = _rows_str(store.query_edn(edn))
    return findings


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

    Defeasible fires are blocking by default (``BLOCKING_DEFEASIBLE = True``).
    When ``BLOCKING_DEFEASIBLE`` is ``True`` and a defeasible query with
    ``severity == "critical"`` returns rows, the function raises ``RuntimeError``.
    """
    meta = _load_defeasible_meta(_ASSETS_ROOT)
    queries = discover_queries(_ASSETS_ROOT)

    # Backend select (REQ-KG-006). DEFAULT cozo (P5.3 cutover): the homoiconic EDN
    # ports run over a Cozo projection of the ledger. ``KG_BACKEND=rdflib`` still
    # selects the legacy SPARQL path (present until the P5.4 deletion). Both return
    # the identical per-query row shape, so the defeasible/BLOCKING logic below is
    # backend-agnostic.
    backend = os.environ.get("KG_BACKEND", "cozo").strip().lower()
    if backend == "cozo":
        per_query = _run_queries_cozo(layout, queries)
    elif backend == "rdflib":
        per_query = _run_queries_rdflib(layout, queries)
    else:
        raise ValueError(
            f"unknown KG_BACKEND {backend!r} (expected 'rdflib' or 'cozo')"
        )

    findings: dict[str, list[tuple]] = {}
    warnings: list[dict] = []
    hard_failures: list[dict] = []

    for cls, name, _query_path in queries:
        rows = per_query[name]
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
