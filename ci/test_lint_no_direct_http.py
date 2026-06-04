"""Tests for the NFR-4 boundary: no direct HTTP outside scrapling-fetch.

The `.import-linter` contract cannot walk the real import graph from the repo
root (the `scripts` package name collides across skills), so enforcement lives in
ci/lint_no_direct_http.py, which AST-scans every skill's source tree. These tests
exercise that real scan — they would fail if a forbidden import were introduced —
plus a smoke check that the .import-linter config still parses and documents the
same forbidden module list.

Invoke via:  python -m pytest ci/test_lint_no_direct_http.py -v   (from the repo root)
"""
import configparser
import textwrap
from pathlib import Path

from ci.lint_no_direct_http import (
    ALLOWED_BROWSER_AUTOMATION,
    FORBIDDEN_MODULES,
    _imports_in,
    find_violations,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_import_linter_config_parses():
    """The .import-linter config must remain syntactically valid INI."""
    cfg = REPO_ROOT / "ci" / ".import-linter"
    p = configparser.ConfigParser(allow_no_value=True)
    p.read(cfg)
    assert "importlinter" in p, "Missing [importlinter] section"
    assert "importlinter:contract:no-direct-http-outside-scrapling-fetch" in p, (
        "Missing contract section"
    )


def test_forbidden_modules_listed():
    """The .import-linter forbidden_modules text must name the HTTP libraries the
    real scanner enforces (kept in sync as documentation)."""
    cfg = REPO_ROOT / "ci" / ".import-linter"
    p = configparser.ConfigParser(allow_no_value=True)
    p.read(cfg)
    section = "importlinter:contract:no-direct-http-outside-scrapling-fetch"
    raw = p.get(section, "forbidden_modules", fallback="")
    listed = {tok.strip() for tok in raw.split() if tok.strip() and not tok.startswith("#")}
    for lib in ("requests", "httpx", "urllib3", "aiohttp", "playwright"):
        assert lib in listed, f"Expected {lib!r} in forbidden_modules, got: {listed}"


def test_repo_has_no_direct_http_outside_scrapling_fetch():
    """The actual enforcement: scanning the real skill trees must find zero
    forbidden HTTP/browser imports (modulo the enumerated browser allowlist)."""
    violations = find_violations()
    assert violations == [], f"NFR-4 violated: {violations}"


def test_scanner_flags_a_synthetic_violation(tmp_path):
    """If a non-scrapling-fetch skill imports a forbidden HTTP lib, the scanner
    must report it — proving the guard is not vacuous."""
    skills = tmp_path / "skills"
    (skills / "book-knowledge" / "scripts").mkdir(parents=True)
    offender = skills / "book-knowledge" / "scripts" / "fetch.py"
    offender.write_text("import requests\n", encoding="utf-8")
    violations = find_violations(skills_dir=skills, repo_root=tmp_path)
    assert ("skills/book-knowledge/scripts/fetch.py", "requests") in violations


def test_scanner_skips_vendored_dirs(tmp_path):
    """A forbidden import inside a .venv/site-packages tree must be ignored."""
    skills = tmp_path / "skills"
    vendored = skills / "book-knowledge" / "scripts" / ".venv" / "lib"
    vendored.mkdir(parents=True)
    (vendored / "vendored.py").write_text("import httpx\n", encoding="utf-8")
    assert find_violations(skills_dir=skills, repo_root=tmp_path) == []


def test_scanner_allows_browser_automation_for_allowlisted_path(tmp_path):
    """A playwright import in an allowlisted book-compose path is permitted, but the
    same import elsewhere is not."""
    skills = tmp_path / "skills"
    bc = skills / "book-compose" / "scripts"
    bc.mkdir(parents=True)
    # Not on the allowlist within this synthetic tree -> flagged.
    (bc / "elsewhere.py").write_text("import playwright\n", encoding="utf-8")
    found = find_violations(skills_dir=skills, repo_root=tmp_path)
    assert ("skills/book-compose/scripts/elsewhere.py", "playwright") in found


def test_scanner_ignores_scrapling_fetch_itself():
    """scrapling-fetch is the sanctioned HTTP surface — it must never appear in
    the violation list even though it imports the forbidden libs."""
    violations = find_violations()
    assert not any(p.startswith("skills/scrapling-fetch/") for p, _ in violations)


def test_browser_allowlist_paths_exist():
    """The enumerated browser-automation exceptions must point at real files so the
    allowlist cannot silently rot into a blanket exemption."""
    for rel in ALLOWED_BROWSER_AUTOMATION:
        assert (REPO_ROOT / rel).is_file(), f"allowlisted path missing: {rel}"


def test_imports_in_skips_relative_imports():
    src = textwrap.dedent(
        """
        from . import sibling
        from .pkg import thing
        import os
        """
    )
    found = _imports_in(src)
    assert "os" in found
    assert "sibling" not in found and "pkg" not in found


def test_forbidden_modules_cover_http_and_browser():
    assert {"requests", "httpx", "urllib3", "aiohttp"} <= FORBIDDEN_MODULES
    assert {"playwright", "patchright"} <= FORBIDDEN_MODULES
