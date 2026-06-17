"""Validate the workspace knowledge graph against the SHACL/booklogic constraints.

Two interchangeable backends assemble the SAME :class:`ShaclReport`
(``conforms`` / ``violations`` / ``text``), selected by the ``KG_BACKEND``
environment variable:

* ``rdflib`` (DEFAULT) — runs pyshacl over the projected TriG dataset against
  ``assets/shapes.ttl``, then NORMALIZES the violations to the canonical
  representation (see below) before returning.
* ``cozo`` — projects the claim ledger into a :class:`CozoStore`, runs the
  ``assets/kg-constraints/*.edn`` constraints (compiled by
  :func:`scripts.booklogic_kg.compile_constraint`) over it, and assembles the
  report from the violation rows.

REQ-KG-012 / REQ-KG-013: the two paths are RESULT-SET equal on the C0.2 goldens
— the bermuda workspace conforms (0 violations) and the C0.1 violating fixture
fails with the same four canonical violations under both engines.

Canonical violation representation (REQ-KG-017 pattern)
-------------------------------------------------------
A violation's identity is ``(focus_node, path, message)`` where:

* ``focus_node`` is the BARE claim/section id (``inj-section``), not the full
  ``{BASE}sections/inj-section`` URI. The Cozo store keys on bare ids; the
  rdflib path's full URIs are stripped down to the same bare id.
* ``message`` is the AUTHORED EDN ``:message`` for the constraint. pyshacl
  auto-generates range / minCount / sh:in messages that differ from the
  hand-written EDN messages, so the rdflib path remaps each violation's message
  (keyed on ``(SHACL path, sourceConstraintComponent)`` — several constraints
  share a path, e.g. status minCount vs sh:in, so the component disambiguates;
  audit I-2) to the authored one. The two ``sh:sparql`` shapes (empty path)
  already emit their authored ``sh:message`` through pyshacl, so those are left
  untouched.
* ``path`` is the SHACL path URI (or ``""`` for the two ``sh:sparql`` shapes).

Callers (book-compose preflight / release bundle) consume ONLY
``report.conforms`` and ``len(report.violations)``, so this canonical
representation is invisible to them; it exists so the two engines can be proven
equivalent. See
``docs/audits/2026-06-17-kg-shacl-representation-divergence.md``.

REQ-KG-002b: this module NEVER imports pycozo. All store access routes through
``scripts.cozo_store`` (the single seam); the constraint compiler is imported
locally from ``scripts.booklogic_kg``.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import edn_format
import pyshacl
from rdflib import Dataset, Graph

from .workspace import WorkspaceLayout

ASSETS = Path(__file__).resolve().parent.parent / "assets"
KG_SCHEMA = ASSETS / "kg-schema.edn"
KG_CONSTRAINTS = ASSETS / "kg-constraints"

# The constraints the Cozo path evaluates, in a fixed order (P2.2 base + P2.3
# chapter-cites-verified + the C-1 confidence-range-low + the P2.4 presence
# arms). Must stay in lockstep with test_booklogic_constraint_compile's
# CONSTRAINT_NAMES. The order only affects the pre-sort emission order; the
# report is sorted before returning.
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

# Bare-id focus URI prefixes minted by project_graph (mirrors project_ledger_cozo's
# _BASE). The rdflib path emits full URIs; the Cozo store keys on bare ids, so the
# canonical form strips these prefixes.
_CLAIM_URI_PREFIX = "https://example.org/book-knowledge/claims/"
_SECTION_URI_PREFIX = "https://example.org/book-knowledge/sections/"


@dataclass(frozen=True)
class Violation:
    focus_node: str
    path: str
    message: str
    # The SHACL sourceConstraintComponent (rdflib path only) — an INTERNAL
    # disambiguator for the message remap, not part of the canonical violation
    # identity. Defaults to "" so the Cozo path and the (focus,path,message)
    # golden are unaffected; callers still see only conforms/violations/text.
    component: str = ""


@dataclass(frozen=True)
class ShaclReport:
    conforms: bool
    violations: list[Violation]
    text: str


# -- canonical representation (the central P2.3 decision) ------------------


def _strip_focus_uri(uri: str) -> str:
    """Strip the claim/section URI prefix to the bare id (else return unchanged)."""
    if uri.startswith(_CLAIM_URI_PREFIX):
        return uri[len(_CLAIM_URI_PREFIX):]
    if uri.startswith(_SECTION_URI_PREFIX):
        return uri[len(_SECTION_URI_PREFIX):]
    return uri


def _build_canonical_messages() -> dict[tuple[str, str], str]:
    """Map each constraint's ``(:path, :component)`` -> authored ``:message``.

    Keyed on ``(SHACL path, sourceConstraintComponent)`` rather than bare path,
    because several constraints share a path: ``status-present`` (minCount) and
    ``status-enum`` (sh:in) both sit on ``tbf:status``; ``confidence-present``
    (minCount), ``confidence-range`` (maxInclusive) and ``confidence-range-low``
    (minInclusive) all sit on ``tbf:confidence``. A path-only key would collapse
    these distinct violations onto one message (internal audit I-2). The component
    URI (declared as ``:component`` in each EDN) is the SHACL discriminator pyshacl
    already reports per violation, so the pair is a stable, unique key.

    Only NON-EMPTY paths are mapped: the two ``sh:sparql`` shapes carry an empty
    path and already emit their authored ``sh:message`` through pyshacl, so they
    must NOT be remapped. Reads the same ``kg-constraints/*.edn`` files the Cozo
    path compiles, so the authored message is the single source of truth for both
    engines. A non-empty-path constraint MUST declare a ``:component``.
    """
    path_kw = edn_format.Keyword("path")
    message_kw = edn_format.Keyword("message")
    component_kw = edn_format.Keyword("component")
    canonical: dict[tuple[str, str], str] = {}
    for name in ACTIVE_CONSTRAINTS:
        form = edn_format.loads(
            (KG_CONSTRAINTS / f"{name}.edn").read_text(encoding="utf-8")
        )
        # Flat form: (defconstraint <name> :message ".." :path ".." ...)
        sections: dict = {}
        i = 2
        while i + 1 < len(form):
            sections[form[i]] = form[i + 1]
            i += 2
        if path_kw not in sections or message_kw not in sections:
            raise ValueError(
                f"constraint EDN '{name}' missing :path or :message key"
            )
        path = sections[path_kw]
        message = sections[message_kw]
        if not path:  # skip the empty-path sh:sparql shapes
            continue
        component = sections.get(component_kw)
        if not component:
            raise ValueError(
                f"constraint EDN '{name}' has a non-empty :path but no "
                f":component (needed to key the rdflib message remap)"
            )
        key = (path, component)
        if key in canonical:
            # Two constraints claim the same (path, component): the remap would
            # silently collapse them (the bug this keying exists to prevent).
            raise ValueError(
                f"duplicate canonical key {key!r} (constraint '{name}' collides "
                f"with an earlier one); give one a distinct :component or :path"
            )
        canonical[key] = message
    return canonical


def _normalize_pyshacl_violations(violations: list[Violation]) -> list[Violation]:
    """Map pyshacl violations to the canonical form, sorted result-set order.

    Bare-id focus_node, authored message looked up by ``(path, component)`` for
    non-empty paths (the empty-path sh:sparql shapes keep pyshacl's authored
    sh:message), SHACL path unchanged. ``component`` is reset to "" on the way out:
    it is an internal remap key, not part of the canonical violation identity.
    """
    canonical = _build_canonical_messages()
    out = [
        Violation(
            focus_node=_strip_focus_uri(v.focus_node),
            path=v.path,
            message=canonical.get((v.path, v.component), v.message),
            component="",
        )
        for v in violations
    ]
    return sorted(out, key=lambda v: (v.focus_node, v.path, v.message))


# -- rdflib backend (default) ----------------------------------------------


def _load_data(layout: WorkspaceLayout) -> Graph:
    ds = Dataset(default_union=True)
    if layout.dataset.exists() and layout.dataset.stat().st_size > 0:
        ds.parse(layout.dataset, format="trig")
    return ds


def _load_shapes(layout: WorkspaceLayout) -> Graph:
    g = Graph()
    if layout.shapes.exists() and layout.shapes.stat().st_size > 0:
        g.parse(layout.shapes, format="turtle")
    else:
        g.parse(ASSETS / "shapes.ttl", format="turtle")
    return g


def _parse_violations(report_graph: Graph) -> list[Violation]:
    from rdflib import URIRef
    out: list[Violation] = []
    for result in report_graph.subjects(predicate=URIRef("http://www.w3.org/ns/shacl#focusNode")):
        focus = report_graph.value(result, URIRef("http://www.w3.org/ns/shacl#focusNode"))
        path = report_graph.value(result, URIRef("http://www.w3.org/ns/shacl#resultPath"))
        msg = report_graph.value(result, URIRef("http://www.w3.org/ns/shacl#resultMessage"))
        comp = report_graph.value(result, URIRef("http://www.w3.org/ns/shacl#sourceConstraintComponent"))
        out.append(Violation(
            focus_node=str(focus) if focus else "",
            path=str(path) if path else "",
            message=str(msg) if msg else "",
            component=str(comp) if comp else "",
        ))
    return out


def _validate_rdflib(layout: WorkspaceLayout) -> ShaclReport:
    data = _load_data(layout)
    shapes = _load_shapes(layout)

    conforms, report_graph, report_text = pyshacl.validate(
        data_graph=data,
        shacl_graph=shapes,
        inference="rdfs",
        allow_warnings=False,
        meta_shacl=False,
        advanced=True,
    )

    raw = _parse_violations(report_graph) if not conforms else []
    # Normalize to the canonical representation so the rdflib path's violation
    # set is result-set equal to the Cozo path's (and to the C0.2 golden).
    violations = _normalize_pyshacl_violations(raw)

    layout.graph_reports.mkdir(parents=True, exist_ok=True)
    (layout.graph_reports / "shacl-latest.txt").write_text(report_text, encoding="utf-8")

    return ShaclReport(conforms=conforms, violations=violations, text=report_text)


# -- cozo backend ----------------------------------------------------------


def _evaluate_constraints(store, schema_path: Path) -> list[Violation]:
    """Run every ACTIVE constraint over ``store`` and collect violation rows.

    For each constraint: read its EDN, compile to a CozoScript rule yielding
    ``[focus, path, message]`` rows, run it, and turn each row into a
    :class:`Violation`. Returns the merged set sorted by
    ``(focus_node, path, message)``. The store is accessed only through the
    ``cozo_store`` seam — this module never imports pycozo (REQ-KG-002b).
    """
    from .booklogic_kg import compile_constraint  # local: keep cost off rdflib path

    violations: list[Violation] = []
    for name in ACTIVE_CONSTRAINTS:
        edn = (KG_CONSTRAINTS / f"{name}.edn").read_text(encoding="utf-8")
        script = compile_constraint(edn, schema_path)
        for row in store.query(script):
            violations.append(
                Violation(focus_node=row[0], path=row[1], message=row[2])
            )
    return sorted(violations, key=lambda v: (v.focus_node, v.path, v.message))


def _cozo_report_text(violations: list[Violation]) -> str:
    """A small human-readable report mirroring pyshacl's conforms/violations gist."""
    conforms = not violations
    lines = [
        "Validation Report (cozo backend)",
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


def _validate_cozo(layout: WorkspaceLayout) -> ShaclReport:
    from .cozo_store import CozoStore  # the single store seam (no pycozo here)
    from .project_ledger_cozo import project_ledger

    store = CozoStore.in_memory(schema_path=KG_SCHEMA)
    project_ledger(layout, store)
    violations = _evaluate_constraints(store, KG_SCHEMA)
    conforms = not violations
    report_text = _cozo_report_text(violations)

    layout.graph_reports.mkdir(parents=True, exist_ok=True)
    (layout.graph_reports / "shacl-latest.txt").write_text(report_text, encoding="utf-8")

    return ShaclReport(conforms=conforms, violations=violations, text=report_text)


# -- dispatch --------------------------------------------------------------


def validate_shacl(layout: WorkspaceLayout) -> ShaclReport:
    """Validate ``layout``'s graph, dispatching on the ``KG_BACKEND`` env var.

    Default is ``rdflib`` (the pyshacl path); ``cozo`` runs the booklogic
    constraints over a Cozo store. Both return an equivalent :class:`ShaclReport`.
    """
    backend = os.environ.get("KG_BACKEND", "rdflib")
    if backend not in ("rdflib", "cozo"):
        raise ValueError(
            f"unknown KG_BACKEND {backend!r} (expected 'rdflib' or 'cozo')"
        )
    if backend == "cozo":
        return _validate_cozo(layout)
    return _validate_rdflib(layout)


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
