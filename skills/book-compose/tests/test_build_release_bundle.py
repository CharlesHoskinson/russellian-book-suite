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

    workspace = workspace_mod.init_workspace(tmp_path / "book")
    layout = workspace_mod.WorkspaceLayout(workspace)
    # (No shapes.ttl copy: validate_shacl is cozo-only — it validates the ledger.)
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
    import json
    import yaml
    workspace = _seed(tmp_path)
    # A verified claim with NO source-span is non-conforming under the Cozo validator
    # (verified-derives + source-span-present fire). append_claim REJECTS a sourceless
    # claim at write time, so write the raw ledger record directly — a real ledger-level
    # defect (replaces the old RDF-injection that only the deleted pyshacl path saw).
    with (workspace / "claims" / "ledger.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "claim_id": "clm-2026-000002",
            "canonical_text": "a verified claim with no provenance",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "source_spans": [],
            "supports_chapters": ["ch-03"],
            "created_at": "2026-01-01T00:00:00+00:00",
        }) + "\n")

    bundle = build_release_bundle(workspace, "ch-03", version="0.2.0", formats=["markdown"])
    manifest = yaml.safe_load((bundle / "manifest.yaml").read_text(encoding="utf-8"))
    # The bundle records the workspace's real non-conforming state, not a hardcoded True.
    assert manifest["shacl_conforms"] is False
