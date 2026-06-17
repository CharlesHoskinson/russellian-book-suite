import pytest

pytestmark = pytest.mark.windows_canary

from datetime import datetime, timezone
from pathlib import Path
import json
import shutil

import pytest
import yaml

from scripts.build_book import build_book, BookBuildError, _autodetect_latest_versions
from scripts.sibling_skills import book_knowledge_root, load_book_knowledge_module


def _seed_minimal_book(tmp_path: Path) -> Path:
    """Two-chapter workspace, both with valid releases."""
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")
    project_graph_mod = load_book_knowledge_module("project_graph")

    bk = book_knowledge_root()
    workspace = workspace_mod.init_workspace(tmp_path / "book")
    layout = workspace_mod.WorkspaceLayout(workspace)

    contracts_dir = workspace / "chapters" / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)

    for n, title, body in [
        (1, "Intro", "# Intro\n\nOpening paragraph.\n\n## Section\n\nMore text.\n"),
        (2, "Body", "# Body\n\nMain content here.\n\n## Detail\n\nMore body.\n"),
    ]:
        cid = f"ch-{n:02d}"
        ledger_mod.append_claim(layout, {
            "claim_id": f"clm-2026-{n:06d}",
            "canonical_text": f"claim {n}",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "source_spans": [{"doc_id": "src", "locator_text": "abcd"}],
            "supports_chapters": [cid],
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        contract = {
            "chapter_id": cid, "title": title,
            "purpose": "purpose long enough to satisfy schema",
            "audience": "senior-engineer", "chapter_type": "reference",
            "evidence_requirements": {"minimum_verified_claims": 0, "max_unresolved_conflicts": 0},
            "acceptance_tests": ["hedge_count == 0"],
            "output_formats": ["markdown"],
        }
        (contracts_dir / f"{cid}.yaml").write_text(yaml.safe_dump(contract), encoding="utf-8")

        release_dir = workspace / "chapters" / "releases" / f"{cid}-v1"
        release_dir.mkdir(parents=True, exist_ok=True)
        (release_dir / "draft.md").write_text(body, encoding="utf-8")
        (release_dir / "manifest.yaml").write_text(yaml.safe_dump({
            "chapter_id": cid, "version": "v1",
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "outputs": ["draft.md"], "sources_included": ["src"],
            "claim_slice_count": 1, "shacl_conforms": True, "competency_clean": True,
        }), encoding="utf-8")

    project_graph_mod.project_graph(layout)
    return workspace


def test_build_book_creates_release_dir(tmp_path):
    workspace = _seed_minimal_book(tmp_path)
    book_dir = build_book(
        workspace, version="1.0.0",
        chapter_versions={"ch-01": "v1", "ch-02": "v1"},
        book_title="Test Book", book_id="test-book",
    )
    assert book_dir == workspace / "book" / "releases" / "1.0.0"
    assert book_dir.is_dir()


def test_build_book_writes_manuscript_md(tmp_path):
    workspace = _seed_minimal_book(tmp_path)
    book_dir = build_book(
        workspace, version="1.0.0",
        chapter_versions={"ch-01": "v1", "ch-02": "v1"},
        book_title="Test Book", book_id="test-book",
    )
    manuscript = (book_dir / "manuscript.md").read_text(encoding="utf-8")
    assert "Intro" in manuscript
    assert "Body" in manuscript


def test_build_book_writes_html_skeleton(tmp_path):
    workspace = _seed_minimal_book(tmp_path)
    book_dir = build_book(
        workspace, version="1.0.0",
        chapter_versions={"ch-01": "v1", "ch-02": "v1"},
        book_title="Test Book", book_id="test-book",
    )
    html = (book_dir / "manuscript.html").read_text(encoding="utf-8")
    assert "Test Book" in html
    assert "BOOK_APP_INSERTION_POINT" in html


def test_build_book_writes_summary_json(tmp_path):
    workspace = _seed_minimal_book(tmp_path)
    book_dir = build_book(
        workspace, version="1.0.0",
        chapter_versions={"ch-01": "v1", "ch-02": "v1"},
        book_title="Test Book", book_id="test-book",
    )
    summary = json.loads((book_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["book_title"] == "Test Book"
    assert len(summary["chapters"]) == 2


def test_build_book_writes_manifest(tmp_path):
    workspace = _seed_minimal_book(tmp_path)
    book_dir = build_book(
        workspace, version="1.0.0",
        chapter_versions={"ch-01": "v1", "ch-02": "v1"},
        book_title="Test Book", book_id="test-book",
    )
    import jsonschema
    schema = json.loads(
        (Path(__file__).resolve().parent.parent / "assets" / "book-manifest.schema.json")
        .read_text(encoding="utf-8")
    )
    manifest = yaml.safe_load((book_dir / "book-manifest.yaml").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    assert manifest["book_id"] == "test-book"
    assert "ch-01" in manifest["chapters_included"]
    assert "ch-02" in manifest["chapters_included"]


def test_build_book_copies_chapter_bundles(tmp_path):
    workspace = _seed_minimal_book(tmp_path)
    book_dir = build_book(
        workspace, version="1.0.0",
        chapter_versions={"ch-01": "v1", "ch-02": "v1"},
        book_title="Test Book", book_id="test-book",
    )
    assert (book_dir / "chapter-bundles" / "ch-01-v1" / "draft.md").exists()
    assert (book_dir / "chapter-bundles" / "ch-02-v1" / "draft.md").exists()


def test_build_book_writes_claims_bibliography(tmp_path):
    workspace = _seed_minimal_book(tmp_path)
    book_dir = build_book(
        workspace, version="1.0.0",
        chapter_versions={"ch-01": "v1", "ch-02": "v1"},
        book_title="Test Book", book_id="test-book",
    )
    bib = (book_dir / "claims-bibliography.jsonl").read_text(encoding="utf-8")
    lines = [line for line in bib.splitlines() if line.strip()]
    assert len(lines) == 2


def test_autodetect_versions_picks_latest(tmp_path):
    workspace = _seed_minimal_book(tmp_path)
    versions = _autodetect_latest_versions(workspace)
    assert versions == {"ch-01": "v1", "ch-02": "v1"}


def test_autodetect_picks_highest_version_not_newest_mtime(tmp_path):
    import os
    import time
    workspace = _seed_minimal_book(tmp_path)
    releases = workspace / "chapters" / "releases"
    # Create a newer semantic version (v2) for ch-01, then make the OLD v1 dir
    # the most-recently-modified so an mtime-based sort would wrongly pick v1.
    v1 = releases / "ch-01-v1"
    v2 = releases / "ch-01-v2"
    shutil.copytree(v1, v2)
    future = time.time() + 1000
    os.utime(v1, (future, future))  # v1 now newest by mtime
    versions = _autodetect_latest_versions(workspace)
    assert versions["ch-01"] == "v2"


def test_manuscript_synthesizes_heading_when_no_h1(tmp_path):
    workspace = _seed_minimal_book(tmp_path)
    # Replace ch-02's draft with one that has no H1 (opens with ## ).
    ch2 = workspace / "chapters" / "releases" / "ch-02-v1" / "draft.md"
    ch2.write_text("## Subsection only\n\nNo top-level heading here.\n", encoding="utf-8")
    book_dir = build_book(
        workspace, version="1.0.0",
        chapter_versions={"ch-01": "v1", "ch-02": "v1"},
        book_title="Test Book", book_id="test-book",
    )
    manuscript = (book_dir / "manuscript.md").read_text(encoding="utf-8")
    # A synthesized chapter heading must be present for ch-02.
    assert "# Chapter 2: Body" in manuscript


def test_manuscript_strips_orphan_citation_tokens(tmp_path):
    workspace = _seed_minimal_book(tmp_path)
    ch1 = workspace / "chapters" / "releases" / "ch-01-v1" / "draft.md"
    ch1.write_text("# Intro\n\nA fact with a leaked token [clm-2026-000001] here.\n",
                   encoding="utf-8")
    book_dir = build_book(
        workspace, version="1.0.0",
        chapter_versions={"ch-01": "v1", "ch-02": "v1"},
        book_title="Test Book", book_id="test-book",
    )
    manuscript = (book_dir / "manuscript.md").read_text(encoding="utf-8")
    html = (book_dir / "manuscript.html").read_text(encoding="utf-8")
    assert "[clm-2026-000001]" not in manuscript
    assert "[clm-2026-000001]" not in html


def test_build_book_fails_when_preflight_fails(tmp_path):
    workspace = _seed_minimal_book(tmp_path)
    with pytest.raises(BookBuildError):
        build_book(
            workspace, version="1.0.0",
            chapter_versions={"ch-01": "v1", "ch-02": "v999"},
            book_title="Test Book", book_id="test-book",
        )
