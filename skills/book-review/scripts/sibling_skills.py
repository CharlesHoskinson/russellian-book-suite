"""Locate sibling skills (book-knowledge, russellian-style, book-compose).

Mirrors the pattern from book-compose, including the alias-namespace
helpers (load_book_knowledge_module, load_russellian_style_module) that
work around the Python module collision when three skills each have a
scripts/ package.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import types
from pathlib import Path


class SiblingNotFoundError(Exception):
    pass


def _skills_root() -> Path:
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    return home / ".claude" / "skills"


def _resolve(name: str) -> Path:
    root = _skills_root() / name
    if not root.is_dir():
        raise SiblingNotFoundError(f"sibling skill not found: {root}")
    if not (root / "SKILL.md").is_file():
        raise SiblingNotFoundError(f"sibling skill missing SKILL.md: {root}")
    return root


def book_knowledge_root() -> Path: return _resolve("book-knowledge")
def russellian_style_root() -> Path: return _resolve("russellian-style")
def book_compose_root() -> Path: return _resolve("book-compose")


_BK_PACKAGE_ALIAS = "_book_knowledge_scripts"
_RS_PACKAGE_ALIAS = "_russellian_style_scripts"
_BC_PACKAGE_ALIAS = "_book_compose_scripts"


def _ensure_package(alias: str, scripts_dir: Path) -> types.ModuleType:
    if alias in sys.modules:
        return sys.modules[alias]
    if not scripts_dir.is_dir():
        raise SiblingNotFoundError(f"scripts dir missing: {scripts_dir}")
    pkg = types.ModuleType(alias)
    pkg.__path__ = [str(scripts_dir)]
    sys.modules[alias] = pkg
    return pkg


def _load_module(alias: str, scripts_dir: Path, name: str) -> types.ModuleType:
    _ensure_package(alias, scripts_dir)
    full_name = f"{alias}.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    module_path = scripts_dir / f"{name}.py"
    if not module_path.is_file():
        raise SiblingNotFoundError(f"module not found: {module_path}")
    spec = importlib.util.spec_from_file_location(full_name, module_path,
                                                  submodule_search_locations=None)
    if spec is None or spec.loader is None:
        raise SiblingNotFoundError(f"could not load spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # Drop the half-executed module so a retry re-raises the original
        # error instead of returning a partial module from the cache.
        sys.modules.pop(full_name, None)
        raise
    return module


def load_book_knowledge_module(name: str) -> types.ModuleType:
    return _load_module(_BK_PACKAGE_ALIAS, book_knowledge_root() / "scripts", name)


def load_russellian_style_module(name: str) -> types.ModuleType:
    return _load_module(_RS_PACKAGE_ALIAS, russellian_style_root() / "scripts", name)


def load_book_compose_module(name: str) -> types.ModuleType:
    return _load_module(_BC_PACKAGE_ALIAS, book_compose_root() / "scripts", name)
