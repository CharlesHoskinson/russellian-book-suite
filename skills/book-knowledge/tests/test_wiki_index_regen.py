from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.wiki_index_regen import wiki_index_regen


def test_regen_lists_all_subdirectories(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    (layout.wiki_sources / "alpha.md").write_text("# Alpha\n", encoding="utf-8")
    (layout.wiki_concepts / "beta.md").write_text("# Beta\n", encoding="utf-8")
    wiki_index_regen(layout)
    text = layout.wiki_index.read_text(encoding="utf-8")
    assert "alpha" in text
    assert "beta" in text
    assert "## Sources" in text
    assert "## Concepts" in text


def test_empty_workspace_yields_empty_sections(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    wiki_index_regen(layout)
    text = layout.wiki_index.read_text(encoding="utf-8")
    assert "## Sources" in text
    assert "(none yet)" in text or "_(empty)_" in text
