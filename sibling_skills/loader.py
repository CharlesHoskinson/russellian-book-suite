from __future__ import annotations
import importlib.util
import os
from pathlib import Path
from types import ModuleType

DEFAULT_ROOT = Path.home() / ".claude" / "skills"


class IncompatibleSkillApiVersion(Exception):
    pass


def _skills_root() -> Path:
    env = os.environ.get("SIBLING_SKILLS_ROOT")
    return Path(env) if env else DEFAULT_ROOT


def load_skill_api(name: str, expected_major: int | None = None) -> ModuleType:
    skill_api_path = _skills_root() / name / "skill_api.py"
    if not skill_api_path.exists():
        raise FileNotFoundError(f"No skill_api.py for skill '{name}' at {skill_api_path}")
    spec = importlib.util.spec_from_file_location(f"{name}.skill_api", skill_api_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if expected_major is not None:
        actual = getattr(module, "API_VERSION", None)
        if actual is None or actual[0] != expected_major:
            raise IncompatibleSkillApiVersion(
                f"Skill '{name}' API_VERSION is {actual}; expected major {expected_major}"
            )
    return module
