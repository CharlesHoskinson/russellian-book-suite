"""Capture golden fixtures of the competency-query + SHACL behaviour (Cozo).

This script freezes the result set of every EDN competency query
(``assets/kg-queries/*.edn``) into a deterministic JSON golden under
``tests/golden/kg/``, plus the SHACL conformance goldens. These are the
equivalence oracle for the homoiconic store (REQ-KG-005). Since the P5.4a cutover
it runs the queries over a Cozo projection of the claim LEDGER
(``project_ledger`` + ``store.query_edn``) — the rdflib/SPARQL/.rq path is gone.

Workspace choice
----------------
The goldens are captured from ``examples/bermuda-manual`` (relative to the repo
root) — the canonical example book — whose committed ledger yields representative,
non-empty results for the coverage and defeasible queries.

Determinism (REQ-KG-008)
------------------------
Each query result is captured as a list of binding dicts (positional keys
``c0..cN``; the comparator compares cell VALUES in sorted-key order) whose values
are coerced to strings, then sorted by a canonical JSON key
(``json.dumps(d, sort_keys=True)``) and serialized with ``sort_keys=True`` so the
goldens are byte-stable across runs and the basis for "result-set equal".

Usage
-----
    python -m scripts.capture_characterization <workspace-dir> <out-dir>

e.g. from ``skills/book-knowledge``::

    .venv/Scripts/python.exe -m scripts.capture_characterization \
        ../../examples/bermuda-manual tests/golden/kg
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .run_competency_queries import discover_queries
from .validate_shacl import validate_shacl
from .workspace import WorkspaceLayout

_SCHEMA = Path(__file__).resolve().parent.parent / "assets" / "kg-schema.edn"

_ASSETS_ROOT = Path(__file__).resolve().parent.parent / "assets"


def _write_golden(payload, out_path: Path) -> None:
    """Serialize ``payload`` as a byte-stable golden JSON file.

    Matches the per-query writer's discipline: ``indent=2, sort_keys=True``, a
    trailing newline, and ``newline="\\n"`` so LF is pinned on every platform
    (the equivalence oracle must not drift on Windows CRLF translation).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def capture_shacl(layout: WorkspaceLayout) -> dict[str, object]:
    """Capture the current pyshacl conformance behaviour as a canonical dict.

    Returns ``{"conforms": bool, "violations": [...]}`` where each violation is
    ``{"focus_node": str, "message": str, "path": str}`` and the violation list
    is sorted canonically by ``json.dumps(v, sort_keys=True)`` -- mirroring
    :func:`_canonical_rows` so the golden is byte-stable across runs (pyshacl
    does not guarantee violation order). This is the equivalence oracle for the
    later SHACL -> EDN -> Cozo port (REQ-KG-014).
    """
    report = validate_shacl(layout)
    violations = [
        {
            "focus_node": str(v.focus_node),
            "message": str(v.message),
            "path": str(v.path),
        }
        for v in report.violations
    ]
    violations.sort(key=lambda v: json.dumps(v, sort_keys=True))
    return {"conforms": report.conforms, "violations": violations}


def write_shacl_golden(layout: WorkspaceLayout, out_path: Path) -> dict:
    """Capture the SHACL report for ``layout`` and write it to ``out_path``.

    Returns the captured dict for reporting. The file is written with the same
    byte-stable style as the per-query goldens.
    """
    payload = capture_shacl(layout)
    _write_golden(payload, out_path)
    return payload


def capture(workspace: Path, out_dir: Path) -> dict[str, int]:
    """Run every EDN competency query over a Cozo projection of the workspace
    ledger and write a canonical golden per query (P5.4a-2: the .rq/rdflib capture
    is gone). Returns a mapping of query name -> row count for reporting.
    """
    from .cozo_store import CozoStore
    from .project_ledger_cozo import project_ledger

    layout = WorkspaceLayout(Path(workspace).resolve())
    if not layout.ledger.exists() or layout.ledger.stat().st_size == 0:
        raise SystemExit(
            f"ERROR: no claims at {layout.ledger}; refusing to write empty goldens"
        )
    store = CozoStore.in_memory(schema_path=_SCHEMA)
    project_ledger(layout, store)
    # Stronger than the file-size guard: refuse when the PROJECTION yields no
    # claims (e.g. a ledger of only-superseded claims), which would otherwise write
    # all-empty goldens — a vacuous oracle. (Faithfully replaces the old "0 triples
    # in the dataset" guard.)
    if not store.query("?[id] := *claim{id}"):
        raise SystemExit(
            f"ERROR: ledger at {layout.ledger} projects zero claims; refusing empty goldens"
        )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    for _cls, name, edn_path in discover_queries(_ASSETS_ROOT):
        # Write SPARQL-binding-dict-shaped goldens (positional keys c0..cN). The
        # query-golden comparator (test_query_ports) compares cell VALUES in
        # sorted-key order, so positional keys reproduce the :find cell order — and
        # keep the committed dict format (a list-of-cells golden would break it).
        golden = [
            {f"c{i}": (str(c) if c is not None else "") for i, c in enumerate(row)}
            for row in store.query_edn(edn_path.read_text(encoding="utf-8"))
        ]
        golden.sort(key=lambda d: json.dumps(d, sort_keys=True))
        _write_golden(golden, out_dir / f"{name}.json")
        counts[name] = len(golden)
    return counts


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "usage: python -m scripts.capture_characterization "
            "<workspace-dir> <out-dir>",
            file=sys.stderr,
        )
        return 2
    counts = capture(Path(argv[1]), Path(argv[2]))
    if not counts:
        print("ERROR: no queries discovered under assets/kg-queries/", file=sys.stderr)
        return 1
    for name, n in counts.items():
        print(f"{name}: {n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
