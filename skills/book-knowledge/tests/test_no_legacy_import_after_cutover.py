"""P5.4 no-legacy-import gate (book-knowledge side) — the SHACL/SPARQL claim stack
is gone. The deferred scan promised in ``test_cutover_gate``'s docstring.

P5.4a deleted the rdflib SHACL/SPARQL claim path (pyshacl, ``shapes.ttl``, the
``.rq`` tree, ``project_graph``). This static scan locks it in: NO script under
``scripts/`` may import ``pyshacl`` or ``pyDatalog``, and ``rdflib`` may be imported
ONLY by ``audit_taxonomy`` — the standalone RDFS taxonomy linter that is explicitly
out of cutover scope (it lints an ontology, not the claim ledger). A new rdflib
importer outside that allowlist fails here rather than silently re-projecting claims
into an RDF graph.

Companion to book-thesis's ``test_no_legacy_import_after_cutover`` (which guards the
pyDatalog consistency pass; rdflib there is allowlisted to the TTL/entailment layer).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

pytestmark = pytest.mark.windows_canary

# The RDFS taxonomy linter is the only sanctioned rdflib user (not a claim path).
RDFLIB_ALLOWLIST = {"audit_taxonomy.py"}

_IMPORT = re.compile(r"^\s*(?:import|from)\s+(rdflib|pyDatalog|pyshacl)\b", re.MULTILINE)


def _imports(path: Path) -> set[str]:
    return set(_IMPORT.findall(path.read_text(encoding="utf-8")))


def test_pyshacl_and_pydatalog_imported_nowhere():
    """The legacy SHACL engine (pyshacl, P5.4a) and pyDatalog are fully removed."""
    offenders = {
        p.name: sorted(mods & {"pyshacl", "pyDatalog"})
        for p in SCRIPTS.glob("*.py")
        if (mods := _imports(p)) & {"pyshacl", "pyDatalog"}
    }
    assert not offenders, f"legacy engine imports must be gone: {offenders}"


def test_rdflib_imported_only_by_audit_taxonomy():
    """No claim-side script projects into rdflib anymore — only the RDFS linter."""
    importers = {p.name for p in SCRIPTS.glob("*.py") if "rdflib" in _imports(p)}
    extra = importers - RDFLIB_ALLOWLIST
    assert not extra, f"rdflib imported outside the cutover allowlist: {sorted(extra)}"


def test_allowlist_is_not_stale():
    """The allowlisted file exists and still imports rdflib (no dead authorization)."""
    for name in RDFLIB_ALLOWLIST:
        path = SCRIPTS / name
        assert path.is_file(), f"allowlisted file missing: {name}"
        assert "rdflib" in _imports(path), f"allowlisted {name} no longer imports rdflib"
