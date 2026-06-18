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

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS = REPO_ROOT / "skills"

pytestmark = pytest.mark.windows_canary

# The RDFS taxonomy linter and thesis TTL/entailment layer are the sanctioned
# rdflib users. Nothing may import pyshacl or pyDatalog.
RDFLIB_ALLOWLIST = {
    REPO_ROOT / "skills" / "book-knowledge" / "scripts" / "audit_taxonomy.py",
    REPO_ROOT / "skills" / "book-thesis" / "scripts" / "compile_thesis.py",
    REPO_ROOT / "skills" / "book-thesis" / "scripts" / "dispatch_entailment.py",
    REPO_ROOT / "skills" / "book-thesis" / "scripts" / "lint_supports.py",
    REPO_ROOT / "skills" / "book-thesis" / "scripts" / "synthesize_exemplars.py",
}
LEGACY_IMPORTS = {"rdflib", "pyDatalog", "pyshacl"}
BANNED_IMPORTS = {"pyDatalog", "pyshacl"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(
                alias.name.split(".", 1)[0]
                for alias in node.names
                if alias.name.split(".", 1)[0] in LEGACY_IMPORTS
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root in LEGACY_IMPORTS:
                found.add(root)
        elif isinstance(node, ast.Call) and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                root = first.value.split(".", 1)[0]
                if root in LEGACY_IMPORTS and _is_dynamic_import_call(node):
                    found.add(root)
    return found


def _is_dynamic_import_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id == "__import__":
        return True
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "import_module"
        and isinstance(func.value, ast.Name)
        and func.value.id == "importlib"
    )


def _script_paths(skills_root: Path) -> list[Path]:
    return sorted(skills_root.glob("*/scripts/**/*.py"))


def _scan_legacy_imports(skills_root: Path) -> dict[str, list[str]]:
    allowlist = {p.resolve() for p in RDFLIB_ALLOWLIST}
    offenders: dict[str, list[str]] = {}
    for path in _script_paths(skills_root):
        imports = _imports(path)
        banned = set(imports & BANNED_IMPORTS)
        if "rdflib" in imports and path.resolve() not in allowlist:
            banned.add("rdflib")
        if banned:
            offenders[path.relative_to(skills_root.parent).as_posix()] = sorted(banned)
    return offenders


def test_pydatalog_and_pyshacl_imported_nowhere():
    """pyDatalog (P5.4b) and pyshacl (P5.4a) are fully removed — no script imports them."""
    offenders = {
        path: [mod for mod in mods if mod in BANNED_IMPORTS]
        for path, mods in _scan_legacy_imports(SKILLS).items()
        if set(mods) & BANNED_IMPORTS
    }
    assert not offenders, f"legacy engine imports must be gone: {offenders}"


def test_rdflib_imported_only_by_allowlisted_files():
    """rdflib stays for the TTL emitter + entailment trio; nothing else may import it."""
    offenders = {
        path: mods
        for path, mods in _scan_legacy_imports(SKILLS).items()
        if "rdflib" in mods
    }
    extra = sorted(offenders)
    assert not extra, f"rdflib imported outside the cutover allowlist: {sorted(extra)}"


def test_allowlist_is_not_stale():
    """Every allowlisted file exists and actually imports rdflib — so the allowlist
    can't quietly authorize a file that no longer needs it (or was deleted)."""
    for path in RDFLIB_ALLOWLIST:
        assert path.is_file(), f"allowlisted file missing: {path}"
        assert "rdflib" in _imports(path), f"allowlisted {path} no longer imports rdflib"


def test_scanner_flags_dynamic_import_literal(tmp_path):
    offender = tmp_path / "offender.py"
    offender.write_text(
        "import importlib\nimportlib.import_module('pyshacl')\n",
        encoding="utf-8",
    )
    assert "pyshacl" in _imports(offender)


def test_scanner_flags_multi_import_alias(tmp_path):
    offender = tmp_path / "offender.py"
    offender.write_text("import os, pyshacl\n", encoding="utf-8")
    assert "pyshacl" in _imports(offender)


def test_scanner_flags_book_compose_scripts(tmp_path):
    offender = tmp_path / "skills" / "book-compose" / "scripts" / "nested" / "offender.py"
    offender.parent.mkdir(parents=True)
    offender.write_text("import pyDatalog\n", encoding="utf-8")
    assert _scan_legacy_imports(tmp_path / "skills") == {
        "skills/book-compose/scripts/nested/offender.py": ["pyDatalog"],
    }
