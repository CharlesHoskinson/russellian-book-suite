from pathlib import Path
from scripts.workspace import init_workspace, find_workspace_root, WorkspaceLayout


def test_init_workspace_creates_full_skeleton(tmp_path):
    root = init_workspace(tmp_path / "my-book")
    expected = [
        "CLAUDE.md",
        "raw/pdf", "raw/markdown", "raw/manifests",
        "wiki/index.md", "wiki/log.md", "wiki/current-status.md",
        "wiki/sources", "wiki/concepts", "wiki/entities", "wiki/chapters",
        "claims/ledger.jsonl", "claims/conflicts.jsonl", "claims/verification",
        "graph/dataset.trig", "graph/shapes.ttl", "graph/imports", "graph/reports",
        "chapters/contracts", "chapters/drafts", "chapters/releases",
        "reports",
    ]
    for relpath in expected:
        assert (root / relpath).exists(), f"missing {relpath}"


def test_init_workspace_is_idempotent(tmp_path):
    target = tmp_path / "my-book"
    root1 = init_workspace(target)
    (root1 / "wiki/log.md").write_text("# Wiki Log\n\nadded by user", encoding="utf-8")
    root2 = init_workspace(target)
    assert root2 == root1
    assert "added by user" in (root2 / "wiki/log.md").read_text(encoding="utf-8")


def test_find_workspace_root_walks_up(tmp_path):
    init_workspace(tmp_path / "book")
    nested = tmp_path / "book" / "wiki" / "concepts"
    nested.mkdir(parents=True, exist_ok=True)
    found = find_workspace_root(nested)
    assert found == tmp_path / "book"


def test_find_workspace_root_returns_none_outside(tmp_path):
    assert find_workspace_root(tmp_path) is None


def test_workspace_layout_paths(tmp_path):
    root = init_workspace(tmp_path / "book")
    layout = WorkspaceLayout(root)
    assert layout.raw_pdf == root / "raw" / "pdf"
    assert layout.ledger == root / "claims" / "ledger.jsonl"
    assert layout.dataset == root / "graph" / "dataset.trig"
    assert layout.shapes == root / "graph" / "shapes.ttl"
