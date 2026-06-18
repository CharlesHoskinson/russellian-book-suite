"""Serialize chapter retrieval bundles for the chapter writer."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .sibling_skills import load_book_knowledge_module


def build_chapter_bundle_input(workspace: Path, chapter_id: str) -> dict[str, Any]:
    """Return JSON/EDN bundle strings and prompt scaffold for ``chapter_id``."""
    projector = load_book_knowledge_module("project_chapter_bundle")
    row = projector.project_chapter_bundle(Path(workspace), chapter_id)
    projector.validate_bundle_payload(row["payload"])
    return {
        "chapter_id": chapter_id,
        "payload": row["payload"],
        "json": row["payload_json"],
        "edn": row["payload_edn"],
        "prompt_scaffold": row["prompt_scaffold"],
    }
