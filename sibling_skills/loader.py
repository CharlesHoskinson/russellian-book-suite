"""Load a sibling skill's public ``skill_api`` from another skill's process.

Sibling skills (scrapling-fetch, book-knowledge, ...) each use absolute
``from scripts.X`` imports, and so does the *calling* skill, so the top-level
``scripts`` package name collides: a naive ``exec_module`` of a sibling's
``skill_api`` resolves ``scripts`` to the caller's scripts dir and fails. Some
siblings bind their ``scripts.X`` dependencies at import time (scrapling-fetch);
others defer them to call time (book-knowledge). A context-managed swap that points
``scripts`` at the sibling during both load and every call handles both, and a thin
proxy applies that swap around each call into the returned api.
"""
from __future__ import annotations

import contextlib
import importlib.util
import inspect
import os
import sys
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".claude" / "skills"


class IncompatibleSkillApiVersion(Exception):
    pass


def _skills_root() -> Path:
    env = os.environ.get("SIBLING_SKILLS_ROOT")
    return Path(env) if env else DEFAULT_ROOT


@contextlib.contextmanager
def _sibling_scripts(root: Path):
    """Make ``scripts`` resolve to ``root/scripts`` for the duration of the block.

    Saves and removes any currently-imported ``scripts``/``scripts.*`` modules,
    points sys.path at the sibling, then restores everything on exit so the
    caller's own ``scripts`` package keeps working afterwards.
    """
    saved_mods = {k: sys.modules.pop(k) for k in list(sys.modules)
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
        sys.modules.update(saved_mods)
        sys.path[:] = saved_path


class _SwappedProxy:
    """Wraps a sibling api module so every call runs with the sibling's scripts active."""

    def __init__(self, root: Path, target):
        object.__setattr__(self, "_root", root)
        object.__setattr__(self, "_target", target)

    def __getattr__(self, name: str):
        val = getattr(object.__getattribute__(self, "_target"), name)
        root = object.__getattribute__(self, "_root")
        if inspect.ismodule(val):
            return _SwappedProxy(root, val)
        if callable(val):
            def wrapper(*args, **kwargs):
                with _sibling_scripts(root):
                    return val(*args, **kwargs)
            wrapper.__name__ = getattr(val, "__name__", name)
            return wrapper
        return val


_CACHE: dict[str, _SwappedProxy] = {}


def load_skill_api(name: str, expected_major: int | None = None) -> _SwappedProxy:
    """Load sibling skill ``name``'s skill_api and return a swap-wrapped proxy.

    ``expected_major``, when given, is checked against the sibling's API_VERSION[0]
    and raises ``IncompatibleSkillApiVersion`` on mismatch.
    """
    root = _skills_root() / name
    skill_api_path = root / "skill_api.py"
    if not skill_api_path.exists():
        raise FileNotFoundError(f"No skill_api.py for skill '{name}' at {skill_api_path}")

    cache_key = str(skill_api_path)
    proxy = _CACHE.get(cache_key)
    if proxy is None:
        mod_name = f"_sibling_{name.replace('-', '_')}_skill_api"
        with _sibling_scripts(root):
            spec = importlib.util.spec_from_file_location(mod_name, str(skill_api_path))
            module = importlib.util.module_from_spec(spec)
            # Register before exec so dataclass/typing machinery can resolve the
            # module by name (`sys.modules[cls.__module__]`) during import.
            sys.modules[mod_name] = module
            spec.loader.exec_module(module)
        proxy = _SwappedProxy(root, module)
        _CACHE[cache_key] = proxy

    if expected_major is not None:
        actual = getattr(object.__getattribute__(proxy, "_target"), "API_VERSION", None)
        if actual is None or tuple(actual)[0] != expected_major:
            raise IncompatibleSkillApiVersion(
                f"Skill '{name}' API_VERSION is {actual}; expected major {expected_major}"
            )
    return proxy
