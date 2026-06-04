import pytest

pytestmark = pytest.mark.windows_canary

from datetime import datetime, timezone
from pathlib import Path
import shutil

import yaml

from scripts.book_preflight import book_preflight, BookPreflightResult
from scripts.sibling_skills import book_knowledge_root, load_book_knowledge_module


def _seed_workspace_with_chapter(tmp_path: Path, chapter_id: str, version: str) -> Path:
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")
    project_graph_mod = load_book_knowledge_module("project_graph")

    bk = book_knowledge_root()
    workspace = workspace_mod.init_workspace(tmp_path / "book")
    layout = workspace_mod.WorkspaceLayout(workspace)
    shutil.copy(bk / "assets" / "shapes.ttl", layout.shapes)
    ledger_mod.append_claim(layout, {
        "claim_id": "clm-2026-000001",
        "canonical_text": "claim canonical",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "small", "locator_text": "abcd"}],
        "supports_chapters": [chapter_id],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    project_graph_mod.project_graph(layout)

    contracts = workspace / "chapters" / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    contract = {
        "chapter_id": chapter_id,
        "title": "Test Chapter",
        "purpose": "purpose long enough to satisfy schema",
        "audience": "senior-engineer",
        "chapter_type": "reference",
        "evidence_requirements": {"minimum_verified_claims": 0, "max_unresolved_conflicts": 0},
        "acceptance_tests": ["hedge_count == 0"],
        "output_formats": ["markdown"],
    }
    (contracts / f"{chapter_id}.yaml").write_text(yaml.safe_dump(contract), encoding="utf-8")

    release_dir = workspace / "chapters" / "releases" / f"{chapter_id}-{version}"
    release_dir.mkdir(parents=True, exist_ok=True)
    (release_dir / "draft.md").write_text(f"# {chapter_id}\n\nBody.\n", encoding="utf-8")
    manifest = {
        "chapter_id": chapter_id,
        "version": version,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "outputs": ["draft.md"],
        "sources_included": ["small"],
        "claim_slice_count": 1,
        "shacl_conforms": True,
        "competency_clean": True,
    }
    (release_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    return workspace


def test_preflight_passes_when_release_exists(tmp_path):
    workspace = _seed_workspace_with_chapter(tmp_path, "ch-01", "v1")
    result = book_preflight(workspace, {"ch-01": "v1"})
    assert isinstance(result, BookPreflightResult)
    assert result.passes is True
    assert result.chapter_count == 1
    assert result.missing_releases == []


def test_preflight_fails_when_release_missing(tmp_path):
    workspace = _seed_workspace_with_chapter(tmp_path, "ch-01", "v1")
    result = book_preflight(workspace, {"ch-01": "v2"})
    assert result.passes is False
    assert "ch-01" in result.missing_releases


def test_preflight_writes_report(tmp_path):
    workspace = _seed_workspace_with_chapter(tmp_path, "ch-01", "v1")
    result = book_preflight(workspace, {"ch-01": "v1"})
    assert result.report_path.exists()
    assert result.report_path.suffix == ".md"


def test_preflight_includes_shacl_status(tmp_path):
    workspace = _seed_workspace_with_chapter(tmp_path, "ch-01", "v1")
    result = book_preflight(workspace, {"ch-01": "v1"})
    assert result.shacl_conforms is True
    assert result.unsupported_claims == 0


def test_preflight_fails_when_chapter_manifest_marked_non_conforming(tmp_path):
    workspace = _seed_workspace_with_chapter(tmp_path, "ch-01", "v1")
    manifest_path = (workspace / "chapters" / "releases" / "ch-01-v1" / "manifest.yaml")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["shacl_conforms"] = False
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    result = book_preflight(workspace, {"ch-01": "v1"})
    # The current workspace still conforms, but the chapter bundle is stamped
    # non-conforming and must not pass preflight.
    assert result.passes is False
    assert "ch-01" in result.missing_releases


def test_preflight_fails_when_chapter_manifest_competency_unclean(tmp_path):
    workspace = _seed_workspace_with_chapter(tmp_path, "ch-01", "v1")
    manifest_path = (workspace / "chapters" / "releases" / "ch-01-v1" / "manifest.yaml")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["competency_clean"] = False
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    result = book_preflight(workspace, {"ch-01": "v1"})
    assert result.passes is False
