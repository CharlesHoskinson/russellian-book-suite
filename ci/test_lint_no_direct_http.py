"""Smoke test for the import-linter contract (NFR-4).

The contract currently has empty source_modules because skill packages are not
yet importable as top-level Python packages from the repo root.  The test
verifies the config is syntactically valid so it will wire cleanly when Phase 4
adds proper package roots.

Invoke via:  ci/.venv/Scripts/python.exe -m pytest ci/test_lint_no_direct_http.py -v
"""
import configparser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_import_linter_config_parses():
    """The .import-linter config must be syntactically valid INI."""
    cfg = REPO_ROOT / "ci" / ".import-linter"
    p = configparser.ConfigParser(allow_no_value=True)
    p.read(cfg)
    assert "importlinter" in p, "Missing [importlinter] section"
    assert "importlinter:contract:no-direct-http-outside-scrapling-fetch" in p, (
        "Missing contract section"
    )


def test_forbidden_modules_listed():
    """The forbidden_modules entry must name the five HTTP libraries."""
    cfg = REPO_ROOT / "ci" / ".import-linter"
    p = configparser.ConfigParser(allow_no_value=True)
    p.read(cfg)
    section = "importlinter:contract:no-direct-http-outside-scrapling-fetch"
    raw = p.get(section, "forbidden_modules", fallback="")
    listed = {tok.strip() for tok in raw.split() if tok.strip() and not tok.startswith("#")}
    for lib in ("requests", "httpx", "urllib3", "aiohttp", "playwright"):
        assert lib in listed, f"Expected {lib!r} in forbidden_modules, got: {listed}"
