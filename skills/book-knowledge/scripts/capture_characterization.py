"""Capture golden fixtures of the current RDF/SPARQL competency-query behavior.

This script freezes the result set of every existing ``.rq`` competency query
into a deterministic JSON golden under ``tests/golden/kg/``. These goldens are
the equivalence oracle for the homoiconic EDN -> Cozo migration (REQ-KG-005):
each later EDN->Cozo port must reproduce its golden exactly.

It changes no production behavior -- it only reads the projected RDF dataset and
runs the queries, reusing the existing machinery in ``run_competency_queries``.

Workspace choice
----------------
The goldens are captured from ``examples/bermuda-manual`` (relative to the repo
root). That workspace ships a committed, non-empty ``graph/dataset.trig`` (the
projected RDF of the bermuda book ledger), so ``_load_dataset`` returns a
populated dataset with no projection step required. It is the canonical example
book in the suite and yields representative, non-empty results for the coverage
and defeasible queries -- making it the right equivalence baseline.

Determinism (REQ-KG-008)
------------------------
Each query result is captured as a list of binding dicts whose values are coerced
to strings, then sorted by a canonical JSON key (``json.dumps(d, sort_keys=True)``)
and serialized with ``sort_keys=True``. SPARQL does not guarantee row order, so
this canonical sort makes the goldens byte-stable across runs and the basis for
"result-set equal" comparison.

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

from .run_competency_queries import _load_dataset, discover_queries
from .validate_shacl import validate_shacl
from .workspace import WorkspaceLayout

_ASSETS_ROOT = Path(__file__).resolve().parent.parent / "assets"


def _canonical_rows(result) -> list[dict[str, str]]:
    """Coerce an rdflib SPARQL result to a canonically-sorted list of str dicts."""
    rows: list[dict[str, str]] = []
    for binding in result:
        row = {str(k): str(v) for k, v in binding.asdict().items()}
        rows.append(row)
    rows.sort(key=lambda d: json.dumps(d, sort_keys=True))
    return rows


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
    """Run every .rq query on ``workspace`` and write a golden per query.

    Returns a mapping of query name -> row count for reporting.
    """
    layout = WorkspaceLayout(Path(workspace).resolve())
    dataset = _load_dataset(layout)
    if len(dataset) == 0:
        raise SystemExit(
            f"ERROR: no triples loaded from {layout.dataset}; refusing to write empty goldens"
        )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    for _cls, name, query_path in discover_queries(_ASSETS_ROOT):
        result = dataset.query(query_path.read_text(encoding="utf-8"))
        rows = _canonical_rows(result)
        _write_golden(rows, out_dir / f"{name}.json")
        counts[name] = len(rows)
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
        print("ERROR: no queries discovered under assets/queries/", file=sys.stderr)
        return 1
    for name, n in counts.items():
        print(f"{name}: {n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
