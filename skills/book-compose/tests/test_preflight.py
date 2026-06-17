import pytest

pytestmark = pytest.mark.windows_canary

from datetime import datetime, timezone
from pathlib import Path
import shutil

import pytest
from scripts.preflight import preflight, PreflightResult
from scripts.sibling_skills import book_knowledge_root, load_book_knowledge_module


def _seed_workspace(tmp_path: Path) -> Path:
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")

    bk = book_knowledge_root()
    workspace = workspace_mod.init_workspace(tmp_path / "book")
    layout = workspace_mod.WorkspaceLayout(workspace)
    ledger_mod.append_claim(layout, {
        "claim_id": "clm-2026-000001",
        "canonical_text": "x" * 10,
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "small", "locator_text": "abcd"}],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    return workspace


def test_preflight_passes_for_clean_workspace(tmp_path):
    workspace = _seed_workspace(tmp_path)
    result = preflight(workspace)
    assert isinstance(result, PreflightResult)
    assert result.passes is True
    assert result.shacl_conforms is True
    assert result.unsupported_claims == 0


def test_preflight_fails_when_workspace_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        preflight(tmp_path / "nonexistent")


def test_preflight_writes_report(tmp_path):
    workspace = _seed_workspace(tmp_path)
    result = preflight(workspace)
    assert result.report_path.exists()
    assert result.report_path.suffix == ".md"
