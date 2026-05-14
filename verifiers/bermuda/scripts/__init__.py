"""Bermuda Verifier — book-knowledge ledger bridge.

Extends the scripts package path to include neurosym-forge's scripts/ so
that `from scripts._edn_reader import ...` resolves correctly regardless of
whether modules are loaded as a package (-m scripts.foo) or directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Repo root is three levels up from this file:
# __init__.py → scripts/ → bermuda/ → verifiers/ → repo-root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_FORGE_SCRIPTS_DIR = str(_REPO_ROOT / "skills" / "neurosym-forge" / "scripts")

# Extend this package's search path so `from scripts._edn_reader import ...`
# finds forge's modules. Guard against double-insertion.
if _FORGE_SCRIPTS_DIR not in __path__:
    __path__.insert(0, _FORGE_SCRIPTS_DIR)
