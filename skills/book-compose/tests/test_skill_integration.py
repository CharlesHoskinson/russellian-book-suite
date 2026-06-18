import pytest

pytestmark = [pytest.mark.windows_canary, pytest.mark.needs_spacy_model]

from datetime import datetime, timezone
from pathlib import Path
import shutil

from scripts.chapter_contract import load_contract
from scripts.preflight import preflight
from scripts.query_chapter_evidence import query_chapter_evidence
from scripts.chapter_contract_check import check_draft
from scripts.build_release_bundle import build_release_bundle
from scripts.sibling_skills import book_knowledge_root, load_book_knowledge_module


def _seed(tmp_path: Path) -> Path:
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")

    bk = book_knowledge_root()
    workspace = workspace_mod.init_workspace(tmp_path / "book")
    layout = workspace_mod.WorkspaceLayout(workspace)

    for i in range(3):
        ledger_mod.append_claim(layout, {
            "claim_id": f"clm-2026-00000{i+1}",
            "canonical_text": f"Verified claim {i+1} for chapter 3.",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9 + i * 0.01,
            "source_spans": [{"doc_id": "small", "page_index": i+1, "locator_text": "abcd"}],
            "supports_chapters": ["ch-03"],
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })

    drafts = workspace / "chapters" / "drafts" / "ch-03"
    drafts.mkdir(parents=True, exist_ok=True)
    (drafts / "draft.md").write_text(
        "# Source Navigation\n\nThe pipeline ingests sources. The wiki accumulates synthesis. The graph records provenance.\n",
        encoding="utf-8",
    )

    contracts = workspace / "chapters" / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    shutil.copy(Path("tests/fixtures/valid_contract.yaml"), contracts / "ch-03.yaml")

    return workspace


def test_full_chapter_compose_pipeline(tmp_path):
    workspace = _seed(tmp_path)

    # Stage 1: contract loading
    contract_path = workspace / "chapters" / "contracts" / "ch-03.yaml"
    contract = load_contract(contract_path)
    assert contract["chapter_id"] == "ch-03"

    # Stage 2: preflight
    pf = preflight(workspace)
    assert pf.passes is True, pf.issues

    # Stage 3: evidence query
    evidence = query_chapter_evidence(workspace, "ch-03")
    assert len(evidence["claims"]) == 3

    # Stage 4: chapter contract check (uses russellian-style linters)
    draft = workspace / "chapters" / "drafts" / "ch-03" / "draft.md"
    style_only_contract = {
        **contract,
        "acceptance_tests": ["hedge_count == 0", "passive_voice_ratio < 0.05"],
    }
    check = check_draft(draft, style_only_contract)
    assert check.passes is True, check.failed_tests

    # Stage 5: release bundle (markdown only — Pandoc may not be installed)
    bundle = build_release_bundle(workspace, "ch-03", version="0.1.0", formats=["markdown"])
    assert (bundle / "draft.md").exists()
    assert (bundle / "manifest.yaml").exists()
    assert (bundle / "evidence-summary.md").exists()
    assert (bundle / "claims-slice.jsonl").exists()

    summary = (bundle / "evidence-summary.md").read_text(encoding="utf-8")
    for cid in ("clm-2026-000001", "clm-2026-000002", "clm-2026-000003"):
        assert cid in summary

    claim_lines = (bundle / "claims-slice.jsonl").read_text(encoding="utf-8").splitlines()
    assert len([line for line in claim_lines if line.strip()]) == 3
