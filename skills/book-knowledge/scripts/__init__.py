"""book-knowledge scripts package.

Extends the scripts package path to include neurosym-forge's scripts/ so
that `from scripts._edn_reader import ...` resolves correctly regardless of
whether modules are loaded as a package (-m scripts.foo) or directly.
"""
from __future__ import annotations

from pathlib import Path

# Repo root is three levels up from this file:
# __init__.py -> scripts/ -> book-knowledge/ -> skills/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_FORGE_SCRIPTS_DIR = str(_REPO_ROOT / "skills" / "neurosym-forge" / "scripts")

# Extend this package's search path so `from scripts._edn_reader import ...`
# finds forge's modules. Append (not insert(0)) so book-knowledge's own modules
# always take precedence on a name collision; forge is only the fallback. Guard
# against double-insertion.
if _FORGE_SCRIPTS_DIR not in __path__:
    __path__.append(_FORGE_SCRIPTS_DIR)
