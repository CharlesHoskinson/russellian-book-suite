import pytest

pytestmark = pytest.mark.windows_canary

from datetime import datetime, timezone
from pathlib import Path
import shutil

from scripts.build_release_bundle import build_release_bundle
from scripts.sibling_skills import book_knowledge_root, load_book_knowledge_module


def _seed(tmp_path: Path) -> Path:
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")
    project_graph_mod = load_book_knowledge_module("project_graph")

    bk = book_knowledge_root()
    workspace = workspace_mod.init_workspace(tmp_path / "book")
    layout = workspace_mod.WorkspaceLayout(workspace)
    shutil.copy(bk / "assets" / "shapes.ttl", layout.shapes)
    ledger_mod.append_claim(layout, {
        "claim_id": "clm-2026-000001",
        "canonical_text": "claim",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "small", "locator_text": "abcd"}],
        "supports_chapters": ["ch-03"],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    project_graph_mod.project_graph(layout)
    drafts = workspace / "chapters" / "drafts" / "ch-03"
    drafts.mkdir(parents=True, exist_ok=True)
    (drafts / "draft.md").write_text("# Chapter 3\n\nA proof body.\n", encoding="utf-8")
    return workspace


def test_release_bundle_produces_markdown(tmp_path):
    workspace = _seed(tmp_path)
    bundle = build_release_bundle(workspace, "ch-03", version="0.1.0", formats=["markdown"])
    assert (bundle / "draft.md").exists()
    assert (bundle / "manifest.yaml").exists()
    assert (bundle / "evidence-summary.md").exists()
    assert (bundle / "claims-slice.jsonl").exists()


def test_release_bundle_manifest_schema_valid(tmp_path):
    workspace = _seed(tmp_path)
    bundle = build_release_bundle(workspace, "ch-03", version="0.1.0", formats=["markdown"])
    import yaml
    import json
    import jsonschema
    schema = json.loads((Path(__file__).resolve().parent.parent / "assets" / "release-manifest.schema.json").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((bundle / "manifest.yaml").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_release_bundle_records_conforming_workspace(tmp_path):
    import yaml
    workspace = _seed(tmp_path)
    bundle = build_release_bundle(workspace, "ch-03", version="0.1.0", formats=["markdown"])
    manifest = yaml.safe_load((bundle / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["shacl_conforms"] is True
    assert manifest["competency_clean"] is True


def test_release_bundle_records_non_conforming_workspace(tmp_path):
    import yaml
    workspace_mod = load_book_knowledge_module("workspace")
    workspace = _seed(tmp_path)
    layout = workspace_mod.WorkspaceLayout(workspace)
    # Inject a verified claim with no provenance into the graph: SHACL must fail.
    bk = book_knowledge_root()
    bad = (bk / "tests" / "fixtures" / "ontology_violations"
           / "unsupported_verified.trig").read_text(encoding="utf-8")
    layout.dataset.write_text(bad, encoding="utf-8")

    bundle = build_release_bundle(workspace, "ch-03", version="0.2.0", formats=["markdown"])
    manifest = yaml.safe_load((bundle / "manifest.yaml").read_text(encoding="utf-8"))
    # The bundle must record the workspace's real non-conforming state, not a hardcoded True.
    assert manifest["shacl_conforms"] is False
