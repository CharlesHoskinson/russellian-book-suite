"""Load book-review's scripts/ modules under an alias namespace.

book-review and review-conductor both ship a `scripts` package. To import
book-review's modules without colliding with our own, we attach them under
the alias `_book_review_scripts`.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path


class SiblingNotFoundError(Exception):
    pass


def _skills_root() -> Path:
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    installed = home / ".claude" / "skills"
    if (installed / "book-review").is_dir():
        return installed
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "skills" / "book-review"
        if candidate.is_dir():
            return parent / "skills"
    raise SiblingNotFoundError("could not locate skills root")


def book_review_root() -> Path:
    root = _skills_root() / "book-review"
    if not root.is_dir():
        raise SiblingNotFoundError(f"book-review not found at {root}")
    if not (root / "SKILL.md").is_file():
        raise SiblingNotFoundError(f"book-review missing SKILL.md at {root}")
    return root


_BR_PACKAGE_ALIAS = "_book_review_scripts"


def _ensure_package(alias: str, scripts_dir: Path) -> types.ModuleType:
    if alias in sys.modules:
        return sys.modules[alias]
    pkg = types.ModuleType(alias)
    pkg.__path__ = [str(scripts_dir)]
    sys.modules[alias] = pkg
    return pkg


def load_book_review_module(name: str) -> types.ModuleType:
    scripts_dir = book_review_root() / "scripts"
    if not scripts_dir.is_dir():
        raise SiblingNotFoundError(f"scripts dir missing: {scripts_dir}")
    _ensure_package(_BR_PACKAGE_ALIAS, scripts_dir)
    full = f"{_BR_PACKAGE_ALIAS}.{name}"
    if full in sys.modules:
        return sys.modules[full]
    module_path = scripts_dir / f"{name}.py"
    if not module_path.is_file():
        raise SiblingNotFoundError(f"module not found: {module_path}")
    spec = importlib.util.spec_from_file_location(full, module_path)
    if spec is None or spec.loader is None:
        raise SiblingNotFoundError(f"could not load spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module
