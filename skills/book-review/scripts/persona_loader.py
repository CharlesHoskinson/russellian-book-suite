"""Load persona definitions from markdown files with YAML frontmatter."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

PERSONAS_DIR = Path(__file__).resolve().parent.parent / "personas"


@dataclass(frozen=True)
class Persona:
    persona_id: str
    display_name: str
    role: str
    body_md: str


_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def load_persona(persona_id: str) -> Persona:
    path = PERSONAS_DIR / f"{persona_id}.md"
    if not path.is_file():
        raise FileNotFoundError(f"persona not found: {path}")
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER.match(text)
    if not match:
        raise ValueError(f"persona {persona_id} missing frontmatter")
    meta = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()
    for required in ("persona_id", "display_name", "role"):
        if required not in meta:
            raise ValueError(f"persona {persona_id} missing required field: {required}")
    return Persona(
        persona_id=meta["persona_id"],
        display_name=meta["display_name"],
        role=meta["role"],
        body_md=body,
    )


def list_personas() -> list[str]:
    if not PERSONAS_DIR.is_dir():
        return []
    return sorted(p.stem for p in PERSONAS_DIR.glob("*.md"))


def load_all() -> list[Persona]:
    return [load_persona(pid) for pid in list_personas()]
