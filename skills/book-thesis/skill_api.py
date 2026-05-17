"""
Public API surface of book-thesis (IF-BT-1).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

API_VERSION = (0, 1)

__all__ = [
    "ThesisNotDefined",
    "ThesisNode",
    "ThesisTree",
    "read_thesis_tree",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ThesisNotDefined(Exception):
    """Raised when no thesis tree exists for the requested chapter."""


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ThesisNode:
    node_id: str
    statement: str
    tags: list[str]
    required_evidence_kind: str
    parent_id: Optional[str]


@dataclass
class ThesisTree:
    chapter_id: str
    nodes: list[ThesisNode]


# ---------------------------------------------------------------------------
# IF-BT-1: read_thesis_tree
#
# Reads <workspace_root>/chapters/<chapter_id>/thesis-tree.yaml.
# Format:
#   chapter_id: <str>
#   nodes:
#     - node_id: <str>
#       statement: <str>
#       tags: [<str>, ...]
#       required_evidence_kind: <str>
#       parent_id: <str | null>
# ---------------------------------------------------------------------------

def read_thesis_tree(chapter_id: str, workspace_root: Path) -> ThesisTree:
    """Read the thesis tree for a chapter.

    Raises ThesisNotDefined if no thesis-tree.yaml exists for the chapter.
    """
    ws = Path(workspace_root)
    tree_path = ws / "chapters" / chapter_id / "thesis-tree.yaml"

    if not tree_path.exists():
        raise ThesisNotDefined(
            f"no thesis tree defined for chapter {chapter_id!r}; "
            f"expected {tree_path}"
        )

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "pyyaml is required to read thesis trees; install it in the skill venv"
        ) from exc

    with tree_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ThesisNotDefined(
            f"thesis-tree.yaml for {chapter_id!r} is not a valid YAML mapping"
        )

    raw_nodes = data.get("nodes") or []
    nodes: list[ThesisNode] = []
    for n in raw_nodes:
        node_id = str(n.get("node_id") or "")
        statement = str(n.get("statement") or "")
        tags = list(n.get("tags") or [])
        req_ev = str(n.get("required_evidence_kind") or "")
        raw_parent = n.get("parent_id")
        parent_id: Optional[str] = None if raw_parent is None else str(raw_parent)
        nodes.append(ThesisNode(
            node_id=node_id,
            statement=statement,
            tags=tags,
            required_evidence_kind=req_ev,
            parent_id=parent_id,
        ))

    resolved_chapter_id = str(data.get("chapter_id") or chapter_id)
    return ThesisTree(chapter_id=resolved_chapter_id, nodes=nodes)
