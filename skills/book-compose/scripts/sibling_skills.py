"""Locate sibling skills (russellian-style, book-knowledge) installed under ~/.claude/skills/."""
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


def russellian_style_root() -> Path:
    return _resolve("russellian-style")


def book_knowledge_root() -> Path:
    return _resolve("book-knowledge")


def workspace_style_overrides_path(workspace: Path) -> Path:
    """Path to the optional workspace-level style overrides JSON file.

    When this file exists, chapter_contract_check sets the
    RUSSELLIAN_OVERRIDES env var to its absolute path before invoking
    russellian-style's linters.
    """
    return Path(workspace) / "style-overrides.json"


def sibling_python(skill_root: Path) -> Path:
    venv_python = skill_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = skill_root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        raise SiblingNotFoundError(f"no venv python under {skill_root / '.venv'}")
    return venv_python


_BK_PACKAGE_ALIAS = "_book_knowledge_scripts"


def _ensure_bk_package() -> types.ModuleType:
    """Register book-knowledge's scripts/ as a synthetic package under an alias.

    book-compose has its own scripts/ package. Importing book-knowledge's
    scripts.workspace by name would collide. We expose book-knowledge's
    scripts/ directory under the alias _book_knowledge_scripts instead.
    """
    if _BK_PACKAGE_ALIAS in sys.modules:
        return sys.modules[_BK_PACKAGE_ALIAS]
    bk_scripts = book_knowledge_root() / "scripts"
    if not bk_scripts.is_dir():
        raise SiblingNotFoundError(f"book-knowledge scripts dir missing: {bk_scripts}")
    pkg = types.ModuleType(_BK_PACKAGE_ALIAS)
    pkg.__path__ = [str(bk_scripts)]  # type: ignore[attr-defined]
    sys.modules[_BK_PACKAGE_ALIAS] = pkg
    return pkg


def load_book_knowledge_module(name: str) -> types.ModuleType:
    """Load a module from book-knowledge/scripts/ under the alias namespace.

    For relative imports inside book-knowledge to work (e.g.
    `from .workspace import WorkspaceLayout`), each module is loaded with
    package = _book_knowledge_scripts.
    """
    _ensure_bk_package()
    full_name = f"{_BK_PACKAGE_ALIAS}.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    bk_scripts = book_knowledge_root() / "scripts"
    module_path = bk_scripts / f"{name}.py"
    if not module_path.is_file():
        raise SiblingNotFoundError(f"book-knowledge module not found: {module_path}")
    spec = importlib.util.spec_from_file_location(
        full_name,
        module_path,
        submodule_search_locations=None,
    )
    if spec is None or spec.loader is None:
        raise SiblingNotFoundError(f"could not load spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


_RS_PACKAGE_ALIAS = "_russellian_style_scripts"


def _ensure_rs_package() -> types.ModuleType:
    if _RS_PACKAGE_ALIAS in sys.modules:
        return sys.modules[_RS_PACKAGE_ALIAS]
    rs_scripts = russellian_style_root() / "scripts"
    if not rs_scripts.is_dir():
        raise SiblingNotFoundError(f"russellian-style scripts dir missing: {rs_scripts}")
    pkg = types.ModuleType(_RS_PACKAGE_ALIAS)
    pkg.__path__ = [str(rs_scripts)]  # type: ignore[attr-defined]
    sys.modules[_RS_PACKAGE_ALIAS] = pkg
    return pkg


def load_russellian_style_module(name: str) -> types.ModuleType:
    _ensure_rs_package()
    full_name = f"{_RS_PACKAGE_ALIAS}.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    rs_scripts = russellian_style_root() / "scripts"
    module_path = rs_scripts / f"{name}.py"
    if not module_path.is_file():
        raise SiblingNotFoundError(f"russellian-style module not found: {module_path}")
    spec = importlib.util.spec_from_file_location(
        full_name,
        module_path,
        submodule_search_locations=None,
    )
    if spec is None or spec.loader is None:
        raise SiblingNotFoundError(f"could not load spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


_BR_PACKAGE_ALIAS = "_book_review_scripts"


def book_review_root() -> Path:
    return _resolve("book-review")


def _ensure_br_package() -> types.ModuleType:
    if _BR_PACKAGE_ALIAS in sys.modules:
        return sys.modules[_BR_PACKAGE_ALIAS]
    br_scripts = book_review_root() / "scripts"
    if not br_scripts.is_dir():
        raise SiblingNotFoundError(f"book-review scripts dir missing: {br_scripts}")
    pkg = types.ModuleType(_BR_PACKAGE_ALIAS)
    pkg.__path__ = [str(br_scripts)]
    sys.modules[_BR_PACKAGE_ALIAS] = pkg
    return pkg


def load_book_review_module(name: str) -> types.ModuleType:
    _ensure_br_package()
    full_name = f"{_BR_PACKAGE_ALIAS}.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    br_scripts = book_review_root() / "scripts"
    module_path = br_scripts / f"{name}.py"
    if not module_path.is_file():
        raise SiblingNotFoundError(f"book-review module not found: {module_path}")
    spec = importlib.util.spec_from_file_location(full_name, module_path,
                                                  submodule_search_locations=None)
    if spec is None or spec.loader is None:
        raise SiblingNotFoundError(f"could not load spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module
