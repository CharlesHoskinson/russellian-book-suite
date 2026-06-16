"""NFR-4 enforcement: no direct HTTP outside scrapling-fetch.

The import-linter `.import-linter` contract cannot walk the real import graph
from the repo root because every skill's code lives under `skills/<name>/scripts/`
and the top-level package name `scripts` collides across skills (it is not
resolvable without per-skill PYTHONPATH juggling). So instead of a documentation-
only contract, this module performs a real AST scan of every skill's source tree
and reports any module that imports a forbidden network/HTTP library.

Policy
------
- The pure HTTP client libraries (requests, httpx, urllib3, aiohttp) are forbidden
  in every skill except scrapling-fetch (the single sanctioned HTTP surface).
- playwright/patchright (browser automation) are forbidden outside scrapling-fetch
  EXCEPT for book-compose's local PDF rendering path, which drives a headless
  Chromium over a `file:///` URL (not network HTTP). That exception is explicit and
  enumerated in ALLOWED_BROWSER_AUTOMATION below so any *new* browser-automation
  import elsewhere is still caught.

Run as a check:  python -m ci.lint_no_direct_http   (exits non-zero on violations)
Tested by:       ci/test_lint_no_direct_http.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"

# The sole sanctioned HTTP surface — its own source is exempt from the scan.
SCRAPLING_FETCH = "scrapling-fetch"

# Pure HTTP clients: forbidden everywhere outside scrapling-fetch.
FORBIDDEN_HTTP = {"requests", "httpx", "urllib3", "aiohttp"}
# Browser automation: forbidden outside scrapling-fetch except where allowlisted.
FORBIDDEN_BROWSER = {"playwright", "patchright"}
FORBIDDEN_MODULES = FORBIDDEN_HTTP | FORBIDDEN_BROWSER

# Explicit, enumerated exceptions for browser-automation imports. Keyed by the
# repo-relative POSIX path of the file that is permitted to import them. These are
# local-rendering paths (file:/// URLs), not network HTTP.
ALLOWED_BROWSER_AUTOMATION = {
    "skills/book-compose/scripts/print_pdf.py",
    "skills/book-compose/scripts/_playwright_check.py",
}


def _top_level(name: str) -> str:
    return name.split(".", 1)[0]


def _imports_in(source: str) -> set[str]:
    """Top-level package names imported by *source* (best-effort; syntax errors -> empty)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(_top_level(alias.name))
        elif isinstance(node, ast.ImportFrom):
            # Skip relative imports (node.level > 0) — they never name a top-level lib.
            if node.level == 0 and node.module:
                found.add(_top_level(node.module))
        elif isinstance(node, ast.Call):
            # Dynamic imports with a string-literal target: __import__("requests")
            # and importlib.import_module("requests") (5.10). Non-literal args
            # (a variable) are out of scope for this static scanner.
            func = node.func
            is_dunder = isinstance(func, ast.Name) and func.id == "__import__"
            is_importlib = isinstance(func, ast.Attribute) and func.attr == "import_module"
            if (is_dunder or is_importlib) and node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                    found.add(_top_level(arg0.value))
    return found


# Directory names that hold third-party / generated code we must not scan — only
# first-party skill source under skills/<name>/scripts/ is in scope for NFR-4.
_EXCLUDED_DIR_PARTS = {".venv", "venv", "site-packages", "__pycache__", "node_modules", ".git"}


def find_violations(skills_dir: Path = SKILLS_DIR, repo_root: Path = REPO_ROOT) -> list[tuple[str, str]]:
    """Return (repo_relative_path, forbidden_module) pairs for every violation.

    Scope is first-party skill source only: skills/<name>/scripts/**.py, excluding
    any vendored/generated directory (.venv, site-packages, __pycache__, ...).
    """
    violations: list[tuple[str, str]] = []
    for py in sorted(skills_dir.rglob("scripts/**/*.py")):
        rel = py.relative_to(repo_root)
        rel_parts = rel.parts
        # skills/<name>/scripts/...
        if len(rel_parts) < 3 or rel_parts[0] != "skills" or rel_parts[2] != "scripts":
            continue
        if _EXCLUDED_DIR_PARTS & set(rel_parts):
            continue
        skill = rel_parts[1]
        if skill == SCRAPLING_FETCH:
            continue
        rel_posix = rel.as_posix()
        try:
            source = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        imported = _imports_in(source)
        for mod in sorted(imported & FORBIDDEN_MODULES):
            if mod in FORBIDDEN_BROWSER and rel_posix in ALLOWED_BROWSER_AUTOMATION:
                continue
            violations.append((rel_posix, mod))
    return violations


def main() -> int:
    violations = find_violations()
    if not violations:
        print("NFR-4 OK: no direct HTTP imports outside scrapling-fetch.")
        return 0
    print("NFR-4 violated: forbidden HTTP/browser imports outside scrapling-fetch:")
    for path, mod in violations:
        print(f"  {path}: imports {mod}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
