from datetime import datetime, timezone
from pathlib import Path
import shutil

import yaml

from scripts.book_summary import collect_chapter_data, build_book_summary
from scripts.sibling_skills import book_knowledge_root, load_book_knowledge_module


def _seed_workspace(tmp_path: Path, chapter_specs: list[tuple[str, str, str]]) -> Path:
    """Each spec is (chapter_id, title, draft_body)."""
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")
    project_graph_mod = load_book_knowledge_module("project_graph")

    bk = book_knowledge_root()
    workspace = workspace_mod.init_workspace(tmp_path / "book")
    layout = workspace_mod.WorkspaceLayout(workspace)
    shutil.copy(bk / "assets" / "shapes.ttl", layout.shapes)

    contracts_dir = workspace / "chapters" / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    for chapter_id, title, body in chapter_specs:
        ledger_mod.append_claim(layout, {
            "claim_id": f"clm-2026-{int(chapter_id.split('-')[1]):06d}",
            "canonical_text": f"verified claim for {chapter_id}",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "source_spans": [{"doc_id": "src", "locator_text": "abcd"}],
            "supports_chapters": [chapter_id],
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        contract = {
            "chapter_id": chapter_id, "title": title,
            "purpose": "purpose long enough to satisfy schema validation",
            "audience": "senior-engineer", "chapter_type": "reference",
            "evidence_requirements": {"minimum_verified_claims": 0, "max_unresolved_conflicts": 0},
            "acceptance_tests": ["hedge_count == 0"],
            "output_formats": ["markdown"],
        }
        (contracts_dir / f"{chapter_id}.yaml").write_text(yaml.safe_dump(contract), encoding="utf-8")

        release_dir = workspace / "chapters" / "releases" / f"{chapter_id}-v1"
        release_dir.mkdir(parents=True, exist_ok=True)
        (release_dir / "draft.md").write_text(body, encoding="utf-8")
        (release_dir / "manifest.yaml").write_text(yaml.safe_dump({
            "chapter_id": chapter_id, "version": "v1",
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "outputs": ["draft.md"], "sources_included": ["src"],
            "claim_slice_count": 1, "shacl_conforms": True, "competency_clean": True,
        }), encoding="utf-8")
    project_graph_mod.project_graph(layout)
    return workspace


SAMPLE_DRAFTS = [
    ("ch-01", "Introduction",
     "# Introduction\n\nFirst paragraph that opens the chapter.\n\n## Overview\n\nMore prose here.\n"),
    ("ch-02", "History",
     "# History\n\nThe history begins long ago.\n\n## Early years\n\nMore historical content.\n"),
    ("ch-03", "Conclusion",
     "# Conclusion\n\nThe summary remarks land here.\n\n## Final thoughts\n\nAnd more closing prose.\n"),
]


def test_collect_chapter_data_returns_one_record_per_chapter(tmp_path):
    workspace = _seed_workspace(tmp_path, SAMPLE_DRAFTS)
    versions = {"ch-01": "v1", "ch-02": "v1", "ch-03": "v1"}
    records = collect_chapter_data(workspace, versions)
    assert len(records) == 3
    titles = {r["title"] for r in records}
    assert titles == {"Introduction", "History", "Conclusion"}


def test_collect_chapter_data_includes_word_count(tmp_path):
    workspace = _seed_workspace(tmp_path, SAMPLE_DRAFTS)
    versions = {"ch-01": "v1", "ch-02": "v1", "ch-03": "v1"}
    records = collect_chapter_data(workspace, versions)
    for r in records:
        assert r["word_count"] > 0


def test_collect_chapter_data_extracts_first_paragraph(tmp_path):
    workspace = _seed_workspace(tmp_path, SAMPLE_DRAFTS)
    versions = {"ch-01": "v1", "ch-02": "v1", "ch-03": "v1"}
    records = collect_chapter_data(workspace, versions)
    intro_record = next(r for r in records if r["chapter_id"] == "ch-01")
    assert "First paragraph" in intro_record["first_paragraph"]


def test_collect_chapter_data_extracts_section_headings(tmp_path):
    workspace = _seed_workspace(tmp_path, SAMPLE_DRAFTS)
    versions = {"ch-01": "v1", "ch-02": "v1", "ch-03": "v1"}
    records = collect_chapter_data(workspace, versions)
    intro = next(r for r in records if r["chapter_id"] == "ch-01")
    assert "Overview" in intro["section_headings"]


def test_build_book_summary_returns_complete_payload(tmp_path):
    workspace = _seed_workspace(tmp_path, SAMPLE_DRAFTS)
    versions = {"ch-01": "v1", "ch-02": "v1", "ch-03": "v1"}
    summary = build_book_summary(workspace, versions, book_title="Test Book")
    assert summary["book_title"] == "Test Book"
    assert summary["total_words"] > 0
    assert summary["total_claims"] == 3
    assert len(summary["chapters"]) == 3
    for ch in summary["chapters"]:
        assert "abstract_seed" in ch
