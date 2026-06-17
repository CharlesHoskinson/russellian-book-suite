"""Load book-knowledge's Cozo modules into book-thesis under an alias (P3.0).

P3 projects the thesis spine into book-knowledge's Cozo store and runs the
EDN->Cozo consistency pass, so book-thesis must import book-knowledge's
``cozo_store`` (store seam) and ``booklogic_kg`` (EDN->CozoScript compiler). The
loader is general (any module by name), but those two are the P3 imports; the
claim-side ``project_ledger_cozo`` is deliberately NOT used, as its transitive
deps would pull book-knowledge's full ledger stack into book-thesis's venv. Both
skills define a top-level ``scripts`` package, so importing ``scripts.cozo_store``
by name would collide; we expose book-knowledge's ``scripts/`` directory under the
synthetic alias package ``_book_knowledge_scripts`` and load each module beneath
it, so the modules' own relative imports (``from .cozo_store import …``) resolve.

Resolution (option b, the repo-self-contained choice): book-knowledge is found
RELATIVE TO book-thesis's own location — the sibling directory next to whichever
copy of book-thesis is running. From the repo that is ``<repo>/skills/book-knowledge``
(carrying the current P2 Cozo work); from an installed checkout it is the
``~/.claude/skills/book-knowledge`` beside the installed book-thesis. A bare
``~/.claude`` fallback is kept only for the unusual case where book-thesis runs
from somewhere without a sibling book-knowledge. This deliberately does NOT prefer
the installed copy first (as book-compose's loader does), because that copy is
frequently stale and lacks the Cozo modules' dependencies — the exact blocker the
P3 handoff flagged.

Mirrors the loader mechanics in book-compose/scripts/sibling_skills.py.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path


class SiblingNotFoundError(Exception):
    pass


def _has_skill(path: Path) -> bool:
    return path.is_dir() and (path / "SKILL.md").is_file()


def book_knowledge_root() -> Path:
    """Resolve book-knowledge: the in-tree sibling first, then ~/.claude.

    The sibling next to this book-thesis copy is authoritative — it is the
    book-knowledge that shares this checkout's state (and, in the repo, its
    P2-current Cozo modules + assets). Only if no sibling exists do we fall back
    to the installed skill.
    """
    # book-thesis/scripts/sibling_skills.py -> scripts -> book-thesis -> skills
    repo_sibling = Path(__file__).resolve().parent.parent.parent / "book-knowledge"
    if _has_skill(repo_sibling):
        return repo_sibling
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    installed = home / ".claude" / "skills" / "book-knowledge"
    if _has_skill(installed):
        return installed
    raise SiblingNotFoundError(
        f"book-knowledge not found beside book-thesis ({repo_sibling}) "
        f"nor under {installed}"
    )


_BK_PACKAGE_ALIAS = "_book_knowledge_scripts"


def _ensure_bk_package() -> types.ModuleType:
    """Register book-knowledge's scripts/ as a synthetic package under an alias.

    book-thesis has its own scripts/ package; importing book-knowledge's
    scripts.cozo_store by name would collide. Expose book-knowledge's scripts/
    directory under the alias _book_knowledge_scripts instead, with __path__ set
    so its modules' relative imports resolve against the alias package.
    """
    bk_scripts = book_knowledge_root() / "scripts"
    if not bk_scripts.is_dir():
        raise SiblingNotFoundError(f"book-knowledge scripts dir missing: {bk_scripts}")
    # The alias is process-global and shared with book-compose's loader (which
    # resolves installed-first). If that loader registered it first, pointing at a
    # DIFFERENT book-knowledge, silently returning it would load the wrong (stale)
    # copy. Validate the cached __path__ and fail loud on mismatch rather than serve
    # the wrong root (audit IMPORTANT — shared-interpreter safety).
    existing = sys.modules.get(_BK_PACKAGE_ALIAS)
    if existing is not None:
        existing_path = list(getattr(existing, "__path__", []) or [])
        if existing_path != [str(bk_scripts)]:
            raise SiblingNotFoundError(
                f"{_BK_PACKAGE_ALIAS} is already registered for a different "
                f"book-knowledge ({existing_path!r} != {[str(bk_scripts)]!r}); "
                f"another skill's loader resolved a different root in this "
                f"interpreter."
            )
        return existing
    pkg = types.ModuleType(_BK_PACKAGE_ALIAS)
    pkg.__path__ = [str(bk_scripts)]  # type: ignore[attr-defined]
    sys.modules[_BK_PACKAGE_ALIAS] = pkg
    return pkg


def load_book_knowledge_module(name: str) -> types.ModuleType:
    """Load a module from book-knowledge/scripts/ under the alias namespace.

    Loaded with package = _book_knowledge_scripts so relative imports inside
    book-knowledge (e.g. ``from .cozo_store import to_snake``) resolve.
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
        full_name, module_path, submodule_search_locations=None
    )
    if spec is None or spec.loader is None:
        raise SiblingNotFoundError(f"could not load spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # Drop the half-executed module so a retry re-raises the original error
        # instead of returning a partial module from the cache.
        sys.modules.pop(full_name, None)
        raise
    return module
