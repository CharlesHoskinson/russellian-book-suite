from pathlib import Path
from scripts.workspace import init_workspace
from scripts.ingest_markdown import ingest_markdown


def test_ingest_markdown_writes_source_summary_and_manifest(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    src = Path("tests/fixtures/small.md")
    result = ingest_markdown(src, workspace)
    assert result["doc_id"] == "small"
    assert (workspace / "raw" / "markdown" / "small.md").exists()
    assert (workspace / "raw" / "manifests" / "small.json").exists()
    assert (workspace / "wiki" / "sources" / "small.md").exists()


def test_ingest_markdown_extracts_heading_tree(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    result = ingest_markdown(Path("tests/fixtures/small.md"), workspace)
    assert result["node_count"] >= 3
    summary = (workspace / "wiki" / "sources" / "small.md").read_text(encoding="utf-8")
    assert "Chapter 1" in summary or "Architecture" in summary
    assert "Chapter 2" in summary or "Validation" in summary


def test_ingest_markdown_is_idempotent(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    src = Path("tests/fixtures/small.md")
    r1 = ingest_markdown(src, workspace)
    r2 = ingest_markdown(src, workspace)
    assert r1["sha256"] == r2["sha256"]


def test_ingest_markdown_appends_log_entry(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    ingest_markdown(Path("tests/fixtures/small.md"), workspace)
    log = (workspace / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "ingest" in log.lower()
    assert "small" in log
