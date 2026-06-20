# skills/voice-eval/scripts/sibling_skills.py
"""Locate and load sibling skills (russellian-style, liveliness-signals,
triadic-voice-v2): the in-repo sibling FIRST, then the installed ~/.claude/skills
copy. Sibling modules use absolute ``from scripts.X`` imports that collide with this
skill's own ``scripts`` package, so each load swaps ``sys.path``/``sys.modules`` for
the sibling and restores them after, returning the loaded module.
"""
from __future__ import annotations

import contextlib
import importlib
import os
import sys
from pathlib import Path

_THIS_SKILL = Path(__file__).resolve().parents[1]      # skills/voice-eval
_SKILLS_DIR = _THIS_SKILL.parent                        # skills/


class SiblingNotFoundError(Exception):
    pass


def _installed_root(name: str) -> Path:
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    return home / ".claude" / "skills" / name


def sibling_root(name: str) -> Path:
    """Repo sibling first, then the installed copy. Must contain SKILL.md."""
    repo = _SKILLS_DIR / name
    if (repo / "SKILL.md").is_file():
        return repo
    installed = _installed_root(name)
    if (installed / "SKILL.md").is_file():
        return installed
    raise SiblingNotFoundError(f"sibling skill not found: {name}")


@contextlib.contextmanager
def _sibling_scripts(root: Path):
    saved = {k: sys.modules.pop(k) for k in list(sys.modules)
             if k == "scripts" or k.startswith("scripts.")}
    saved_path = sys.path[:]
    try:
        sys.path.insert(0, str(root))
        importlib.invalidate_caches()
        yield
    finally:
        for k in list(sys.modules):
            if k == "scripts" or k.startswith("scripts."):
                del sys.modules[k]
        sys.modules.update(saved)
        sys.path[:] = saved_path


def load_module(skill: str, dotted: str):
    """Import ``dotted`` (e.g. 'scripts.score') from sibling ``skill`` and return it.

    The returned module's functions must be called *inside* a ``using(skill)`` block
    when they themselves import sibling ``scripts.*`` at call time. The pure helpers
    we use (score_passage, voice_eval.evaluate, brief.build_generation_brief) bind
    their deps at import, so a plain post-load call is safe — but we re-enter the
    swap on each call via ``call`` for safety.
    """
    root = sibling_root(skill)
    with _sibling_scripts(root):
        return importlib.import_module(dotted)


def call(skill: str, dotted: str, func: str, *args, **kwargs):
    """Import ``skill``'s ``dotted`` module and call ``func`` with the sibling's
    ``scripts`` active for the duration of the call."""
    root = sibling_root(skill)
    with _sibling_scripts(root):
        mod = importlib.import_module(dotted)
        return getattr(mod, func)(*args, **kwargs)
