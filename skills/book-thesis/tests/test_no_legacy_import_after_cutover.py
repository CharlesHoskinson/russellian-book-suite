"""P5.4 no-legacy-import gate (book-thesis side) — pyDatalog is gone for good.

The cutover deleted the pyDatalog consistency pass (P5.4b). This static scan locks
that in: NO script under ``scripts/`` may import ``pyDatalog`` or ``pyshacl``, and
``rdflib`` may be imported ONLY by the files that legitimately keep the RDF/TTL
layer — ``compile_thesis`` (emits the thesis triples) and the book-thesis-entailment
trio (``dispatch_entailment``/``lint_supports``/``synthesize_exemplars``) that parse
those triples. A new rdflib importer outside the allowlist, or any pyDatalog import
creeping back, fails here rather than silently re-growing the legacy stack.

Companion to book-knowledge's ``test_no_legacy_import_after_cutover`` (which guards
the pyshacl/SPARQL claim stack; rdflib there is allowlisted to ``audit_taxonomy``).
"""
from __future__ import annotations

import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

# Files allowed to import rdflib: the TTL emitter + the entailment layer that reads it.
RDFLIB_ALLOWLIST = {
    "compile_thesis.py",
    "dispatch_entailment.py",
    "lint_supports.py",
    "synthesize_exemplars.py",
}

_IMPORT = re.compile(r"^\s*(?:import|from)\s+(rdflib|pyDatalog|pyshacl)\b", re.MULTILINE)


def _imports(path: Path) -> set[str]:
    return set(_IMPORT.findall(path.read_text(encoding="utf-8")))


def test_pydatalog_and_pyshacl_imported_nowhere():
    """pyDatalog (P5.4b) and pyshacl (P5.4a) are fully removed — no script imports them."""
    offenders = {
        p.name: sorted(mods & {"pyDatalog", "pyshacl"})
        for p in SCRIPTS.glob("*.py")
        if (mods := _imports(p)) & {"pyDatalog", "pyshacl"}
    }
    assert not offenders, f"legacy engine imports must be gone: {offenders}"


def test_rdflib_imported_only_by_allowlisted_files():
    """rdflib stays for the TTL emitter + entailment trio; nothing else may import it."""
    importers = {p.name for p in SCRIPTS.glob("*.py") if "rdflib" in _imports(p)}
    extra = importers - RDFLIB_ALLOWLIST
    assert not extra, f"rdflib imported outside the cutover allowlist: {sorted(extra)}"


def test_allowlist_is_not_stale():
    """Every allowlisted file exists and actually imports rdflib — so the allowlist
    can't quietly authorize a file that no longer needs it (or was deleted)."""
    for name in RDFLIB_ALLOWLIST:
        path = SCRIPTS / name
        assert path.is_file(), f"allowlisted file missing: {name}"
        assert "rdflib" in _imports(path), f"allowlisted {name} no longer imports rdflib"
