"""Validate the workspace knowledge graph against the booklogic/EDN constraints.

Cozo is the sole backend (the legacy rdflib/pyshacl path was removed in P5.4a): the
claim ledger is projected into a :class:`CozoStore` and the
``assets/kg-constraints/*.edn`` constraints (compiled by
:func:`scripts.booklogic_kg.compile_constraint`) run over it, assembling a
:class:`ShaclReport` (``conforms`` / ``violations`` / ``text``). Callers
(book-compose preflight / release bundle) consume only ``report.conforms`` and
``len(report.violations)``.

REQ-KG-002b: this module NEVER imports pycozo. All store access routes through
``scripts.cozo_store`` (the single seam); the constraint compiler is imported
locally from ``scripts.booklogic_kg``.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from .workspace import WorkspaceLayout

ASSETS = Path(__file__).resolve().parent.parent / "assets"
KG_SCHEMA = ASSETS / "kg-schema.edn"
KG_CONSTRAINTS = ASSETS / "kg-constraints"

# The constraints evaluated, in a fixed order. Must stay in lockstep with
# test_booklogic_constraint_compile's CONSTRAINT_NAMES. The order only affects the
# pre-sort emission order; the report is sorted before returning.
ACTIVE_CONSTRAINTS = [
    "status-enum",
    "status-present",
    "confidence-range",
    "confidence-range-low",
    "confidence-present",
    "text-cardinality",
    "source-span-present",
    "verified-derives",
    "chapter-cites-verified",
]


@dataclass(frozen=True)
class Violation:
    focus_node: str
    path: str
    message: str


@dataclass(frozen=True)
class ShaclReport:
    conforms: bool
    violations: list[Violation]
    text: str


def _evaluate_constraints(store, schema_path: Path) -> list[Violation]:
    """Run every ACTIVE constraint over ``store`` and collect violation rows.

    For each constraint: read its EDN, compile to a CozoScript rule yielding
    ``[focus, path, message]`` rows, run it, and turn each row into a
    :class:`Violation`. Returns the merged set sorted by
    ``(focus_node, path, message)``. The store is accessed only through the
    ``cozo_store`` seam — this module never imports pycozo (REQ-KG-002b).
    """
    from .booklogic_kg import compile_constraint  # local: avoid import cost/cycle

    violations: list[Violation] = []
    for name in ACTIVE_CONSTRAINTS:
        edn = (KG_CONSTRAINTS / f"{name}.edn").read_text(encoding="utf-8")
        script = compile_constraint(edn, schema_path)
        for row in store.query(script):
            violations.append(
                Violation(focus_node=row[0], path=row[1], message=row[2])
            )
    return sorted(violations, key=lambda v: (v.focus_node, v.path, v.message))


def _report_text(violations: list[Violation]) -> str:
    """A small human-readable report (conforms/violations gist)."""
    conforms = not violations
    lines = [
        "Validation Report",
        f"Conforms: {conforms}",
        f"Results ({len(violations)}):",
    ]
    for v in violations:
        lines.append(
            f"Constraint Violation:\n"
            f"\tFocus Node: {v.focus_node}\n"
            f"\tResult Path: {v.path}\n"
            f"\tMessage: {v.message}"
        )
    return "\n".join(lines) + "\n"


def validate_shacl(layout: WorkspaceLayout) -> ShaclReport:
    """Validate ``layout``'s claim graph by running the EDN constraints over Cozo.

    Projects the ledger into an in-memory :class:`CozoStore`, evaluates every
    ACTIVE constraint, and assembles the :class:`ShaclReport`.
    """
    from .cozo_store import CozoStore  # the single store seam (no pycozo here)
    from .project_ledger_cozo import project_ledger

    store = CozoStore.in_memory(schema_path=KG_SCHEMA)
    project_ledger(layout, store)
    violations = _evaluate_constraints(store, KG_SCHEMA)
    report_text = _report_text(violations)

    layout.graph_reports.mkdir(parents=True, exist_ok=True)
    (layout.graph_reports / "shacl-latest.txt").write_text(report_text, encoding="utf-8")

    return ShaclReport(conforms=not violations, violations=violations, text=report_text)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_shacl.py <workspace-dir>", file=sys.stderr)
        return 2
    layout = WorkspaceLayout(Path(argv[1]))
    report = validate_shacl(layout)
    print(report.text)
    return 0 if report.conforms else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
