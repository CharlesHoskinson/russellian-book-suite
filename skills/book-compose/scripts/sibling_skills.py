"""Locate sibling skills (russellian-style, book-knowledge, feynman-style,
book-review, review-conductor, book-qa): the in-repo sibling FIRST, then the installed
~/.claude/skills/ copy, and load their scripts under guarded alias packages."""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import types
from pathlib import Path


class SiblingNotFoundError(Exception):
    pass


def _canon(p) -> str:
    """Canonical path key: realpath + normcase, so the same directory reached via a
    junction/symlink or different Windows casing compares equal."""
    return os.path.normcase(os.path.realpath(str(p)))


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


def _repo_sibling(name: str) -> Path:
    """Resolve a sibling skill: the in-repo sibling FIRST, then the installed copy.

    Repo-first (the P5.1 / P3.0 convention) because the installed
    ``~/.claude/skills/<name>`` is frequently stale and may be absent entirely
    (e.g. on a box where the skill was never globally installed); the sibling
    next to this book-compose checkout shares its current state. Falls back to
    ``_resolve`` only when no repo sibling is present.
    """
    repo_sibling = Path(__file__).resolve().parent.parent.parent / name
    if repo_sibling.is_dir() and (repo_sibling / "SKILL.md").is_file():
        return repo_sibling
    return _resolve(name)


def _register_alias(alias: str, scripts_dir: Path, label: str) -> types.ModuleType:
    """Register ``scripts_dir`` as a synthetic package under ``alias`` in
    ``sys.modules`` so a sibling skill's relative imports resolve without
    colliding with book-compose's own top-level ``scripts`` package.

    The alias is process-global (shared across loaders and with book-thesis). If
    it is already registered for a DIFFERENT root, serving it would load the wrong
    copy, so validate the cached ``__path__`` (canonicalised so a junction/symlink
    or Windows-casing difference to the SAME dir is not a false mismatch) and fail
    loud on a real mismatch rather than silently blending two trees.
    """
    if not scripts_dir.is_dir():
        raise SiblingNotFoundError(f"{label} scripts dir missing: {scripts_dir}")
    existing = sys.modules.get(alias)
    if existing is not None:
        existing_path = [_canon(p) for p in (getattr(existing, "__path__", []) or [])]
        if existing_path != [_canon(scripts_dir)]:
            raise SiblingNotFoundError(
                f"{alias} is already registered for a different {label} "
                f"({existing_path!r} != {[_canon(scripts_dir)]!r})"
            )
        return existing
    pkg = types.ModuleType(alias)
    pkg.__path__ = [str(scripts_dir)]  # type: ignore[attr-defined]
    sys.modules[alias] = pkg
    return pkg


def russellian_style_root() -> Path:
    return _repo_sibling("russellian-style")


def book_knowledge_root() -> Path:
    return _repo_sibling("book-knowledge")


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
    return _register_alias(_BK_PACKAGE_ALIAS, book_knowledge_root() / "scripts", "book-knowledge")


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
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # Drop the half-executed module so a retry re-raises the original
        # error instead of returning a partial module from the cache.
        sys.modules.pop(full_name, None)
        raise
    return module


_RS_PACKAGE_ALIAS = "_russellian_style_scripts"


def _ensure_rs_package() -> types.ModuleType:
    return _register_alias(_RS_PACKAGE_ALIAS, russellian_style_root() / "scripts", "russellian-style")


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
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # Drop the half-executed module so a retry re-raises the original
        # error instead of returning a partial module from the cache.
        sys.modules.pop(full_name, None)
        raise
    return module


_FS_PACKAGE_ALIAS = "_feynman_style_scripts"


def feynman_style_root() -> Path:
    return _repo_sibling("feynman-style")


def _ensure_fs_package() -> types.ModuleType:
    return _register_alias(_FS_PACKAGE_ALIAS, feynman_style_root() / "scripts", "feynman-style")


def load_feynman_style_module(name: str) -> types.ModuleType:
    """Load a module from feynman-style/scripts/ under an alias namespace.

    Mirrors load_russellian_style_module. feynman-style's linters use relative
    imports (e.g. `from .lint_common import ...`); loading them under the
    _feynman_style_scripts alias package resolves those relatives without
    colliding with book-compose's own top-level `scripts` package.
    """
    _ensure_fs_package()
    full_name = f"{_FS_PACKAGE_ALIAS}.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    fs_scripts = feynman_style_root() / "scripts"
    module_path = fs_scripts / f"{name}.py"
    if not module_path.is_file():
        raise SiblingNotFoundError(f"feynman-style module not found: {module_path}")
    spec = importlib.util.spec_from_file_location(
        full_name,
        module_path,
        submodule_search_locations=None,
    )
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


def feynman_classify_linter(rule: str) -> str:
    """Return 'surface' or 'integrity' for a Feynman/Russell rule name, per
    feynman-style's assets/feynman-rules.json. Defaults to 'surface' for
    unknown rules. Loaded directly from the JSON asset to avoid importing
    feynman-style's skill_api (which would collide with book-compose's own
    top-level `scripts` package)."""
    import json as _json
    rules_path = feynman_style_root() / "assets" / "feynman-rules.json"
    data = _json.loads(rules_path.read_text(encoding="utf-8"))
    return data.get("linter_class", {}).get(rule, "surface")


_BR_PACKAGE_ALIAS = "_book_review_scripts"


def book_review_root() -> Path:
    return _repo_sibling("book-review")


def _ensure_br_package() -> types.ModuleType:
    return _register_alias(_BR_PACKAGE_ALIAS, book_review_root() / "scripts", "book-review")


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
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # Drop the half-executed module so a retry re-raises the original
        # error instead of returning a partial module from the cache.
        sys.modules.pop(full_name, None)
        raise
    return module


_BQ_PACKAGE_ALIAS = "_book_qa_scripts"


def book_qa_root() -> Path:
    return _repo_sibling("book-qa")


def _ensure_bq_package() -> types.ModuleType:
    return _register_alias(_BQ_PACKAGE_ALIAS, book_qa_root() / "scripts", "book-qa")


def load_book_qa_module(name: str) -> types.ModuleType:
    _ensure_bq_package()
    full_name = f"{_BQ_PACKAGE_ALIAS}.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    bq_scripts = book_qa_root() / "scripts"
    module_path = bq_scripts / f"{name}.py"
    if not module_path.is_file():
        raise SiblingNotFoundError(f"book-qa module not found: {module_path}")
    spec = importlib.util.spec_from_file_location(full_name, module_path,
                                                  submodule_search_locations=None)
    if spec is None or spec.loader is None:
        raise SiblingNotFoundError(f"could not load spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(full_name, None)
        raise
    return module


_RC_PACKAGE_ALIAS = "_review_conductor_scripts"


def review_conductor_root() -> Path:
    return _repo_sibling("review-conductor")


def _ensure_rc_package() -> types.ModuleType:
    return _register_alias(_RC_PACKAGE_ALIAS, review_conductor_root() / "scripts", "review-conductor")


def load_review_conductor_module(name: str) -> types.ModuleType:
    _ensure_rc_package()
    full_name = f"{_RC_PACKAGE_ALIAS}.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    rc_scripts = review_conductor_root() / "scripts"
    module_path = rc_scripts / f"{name}.py"
    if not module_path.is_file():
        raise SiblingNotFoundError(f"review-conductor module not found: {module_path}")
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
