from pathlib import Path
from scripts.workspace import init_workspace
from scripts.ingest_pdf import ingest_pdf


def test_ingest_pdf_writes_manifest_and_summary(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    result = ingest_pdf(Path("tests/fixtures/small.pdf"), workspace)
    assert result["doc_id"] == "small"
    assert result["page_count"] == 3
    assert (workspace / "raw" / "pdf" / "small.pdf").exists()
    assert (workspace / "raw" / "manifests" / "small.json").exists()
    assert (workspace / "wiki" / "sources" / "small.md").exists()


def test_ingest_pdf_extracts_text_per_page(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    ingest_pdf(Path("tests/fixtures/small.pdf"), workspace)
    summary = (workspace / "wiki" / "sources" / "small.md").read_text(encoding="utf-8")
    assert "Architecture" in summary
    assert "Validation" in summary
    assert "Provenance" in summary


def test_ingest_pdf_records_node_count(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    result = ingest_pdf(Path("tests/fixtures/small.pdf"), workspace)
    assert result["node_count"] == 3
