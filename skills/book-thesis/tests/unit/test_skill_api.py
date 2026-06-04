"""Unit tests for the book-thesis public skill_api surface (IF-BT-1)."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from skill_api import (
    read_thesis_tree,
    ThesisTree,
    ThesisNode,
    ThesisNotDefined,
    API_VERSION,
)


# ---------------------------------------------------------------------------
# Helpers: minimal workspace with thesis-tree YAML
# ---------------------------------------------------------------------------

MINIMAL_TREE_YAML = """\
chapter_id: ch-01
nodes:
  - node_id: root-claim
    statement: The root claim of chapter one.
    tags: [finality, safety]
    required_evidence_kind: empirical
    parent_id: null
  - node_id: sub-claim-a
    statement: Sub-claim A supports the root.
    tags: [finality]
    required_evidence_kind: logical
    parent_id: root-claim
"""


def _make_workspace(tmp_path: Path, chapter_id: str, yaml_text: str) -> Path:
    ws = tmp_path / "book"
    ws.mkdir()
    chapters_dir = ws / "chapters" / chapter_id
    chapters_dir.mkdir(parents=True)
    (chapters_dir / "thesis-tree.yaml").write_text(yaml_text, encoding="utf-8")
    return ws


# ---------------------------------------------------------------------------
# IF-BT-0: API surface
# ---------------------------------------------------------------------------

def test_api_version():
    assert API_VERSION == (0, 1)


# ---------------------------------------------------------------------------
# IF-BT-1: read_thesis_tree
# ---------------------------------------------------------------------------

def test_read_thesis_tree_returns_thesis_tree(tmp_path):
    ws = _make_workspace(tmp_path, "ch-01", MINIMAL_TREE_YAML)
    tree = read_thesis_tree("ch-01", ws)
    assert isinstance(tree, ThesisTree)


def test_read_thesis_tree_chapter_id(tmp_path):
    ws = _make_workspace(tmp_path, "ch-01", MINIMAL_TREE_YAML)
    tree = read_thesis_tree("ch-01", ws)
    assert tree.chapter_id == "ch-01"


def test_read_thesis_tree_nodes(tmp_path):
    ws = _make_workspace(tmp_path, "ch-01", MINIMAL_TREE_YAML)
    tree = read_thesis_tree("ch-01", ws)
    assert len(tree.nodes) == 2
    assert all(isinstance(n, ThesisNode) for n in tree.nodes)


def test_read_thesis_tree_node_fields(tmp_path):
    ws = _make_workspace(tmp_path, "ch-01", MINIMAL_TREE_YAML)
    tree = read_thesis_tree("ch-01", ws)
    root = next(n for n in tree.nodes if n.node_id == "root-claim")
    assert root.statement == "The root claim of chapter one."
    assert root.tags == ["finality", "safety"]
    assert root.required_evidence_kind == "empirical"
    assert root.parent_id is None


def test_read_thesis_tree_child_node_parent(tmp_path):
    ws = _make_workspace(tmp_path, "ch-01", MINIMAL_TREE_YAML)
    tree = read_thesis_tree("ch-01", ws)
    child = next(n for n in tree.nodes if n.node_id == "sub-claim-a")
    assert child.parent_id == "root-claim"


def test_read_thesis_tree_stable_node_ids(tmp_path):
    ws = _make_workspace(tmp_path, "ch-01", MINIMAL_TREE_YAML)
    tree1 = read_thesis_tree("ch-01", ws)
    tree2 = read_thesis_tree("ch-01", ws)
    ids1 = [n.node_id for n in tree1.nodes]
    ids2 = [n.node_id for n in tree2.nodes]
    assert ids1 == ids2


def test_read_thesis_tree_raises_for_missing_chapter(tmp_path):
    ws = tmp_path / "book"
    ws.mkdir()
    with pytest.raises(ThesisNotDefined):
        read_thesis_tree("ch-99", ws)
