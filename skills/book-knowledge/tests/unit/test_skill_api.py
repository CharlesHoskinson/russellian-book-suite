"""Unit tests for the book-knowledge public skill_api surface (IF-BK-1..4)."""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

# The skill_api lives at the skill root, not under scripts/.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from skill_api import (
    ingest_pdf,
    query_claims,
    is_source_ingested,
    list_concepts,
    IngestResult,
    ClaimRecord,
    ClaimFilter,
    ConceptRef,
    API_VERSION,
)
from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ledger import append_claim

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SMALL_PDF = FIXTURES / "small.pdf"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stub_claim(claim_id: str = "clm-2026-000001", status: str = "proposed",
                tags: list[str] | None = None) -> dict:
    record: dict = {
        "claim_id": claim_id,
        "canonical_text": "Atomic propositions are independently verifiable.",
        "status": status,
        "claim_type": "fact",
        "confidence": 0.85,
        "source_spans": [{"doc_id": "small", "page_index": 1,
                           "locator_text": "p.1 three components"}],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if tags:
        record["semantic_class"] = tags[0]
    return record


def _make_workspace(tmp_path: Path) -> Path:
    return init_workspace(tmp_path / "book")


# ---------------------------------------------------------------------------
# IF-BK-0: API surface sanity
# ---------------------------------------------------------------------------

def test_api_version():
    assert API_VERSION == (0, 1)


# ---------------------------------------------------------------------------
# IF-BK-1: ingest_pdf
# ---------------------------------------------------------------------------

def test_ingest_pdf_returns_ingest_result(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ingest_pdf(SMALL_PDF, ws)
    assert isinstance(result, IngestResult)


def test_ingest_pdf_status_ingested_for_novel_pdf(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ingest_pdf(SMALL_PDF, ws)
    assert result.status == "ingested"
    assert result.sha256 != ""
    assert result.claims_extracted >= 0


def test_ingest_pdf_status_already_present_for_duplicate(tmp_path):
    ws = _make_workspace(tmp_path)
    ingest_pdf(SMALL_PDF, ws)
    result2 = ingest_pdf(SMALL_PDF, ws)
    assert result2.status == "already_present"


def test_ingest_pdf_source_id_is_non_empty(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ingest_pdf(SMALL_PDF, ws)
    assert result.source_id != ""


# ---------------------------------------------------------------------------
# IF-BK-2: query_claims
# ---------------------------------------------------------------------------

def test_query_claims_empty_filter_returns_all(tmp_path):
    ws = _make_workspace(tmp_path)
    layout = WorkspaceLayout(ws)
    for i in range(1, 4):
        append_claim(layout, _stub_claim(claim_id=f"clm-2026-{i:06d}"))
    results = query_claims(ClaimFilter(), ws)
    assert len(results) == 3
    assert all(isinstance(r, ClaimRecord) for r in results)


def test_query_claims_filter_by_tags(tmp_path):
    ws = _make_workspace(tmp_path)
    layout = WorkspaceLayout(ws)
    for i in range(1, 4):
        append_claim(layout, _stub_claim(claim_id=f"clm-2026-{i:06d}", tags=["finality"]))
    for i in range(4, 6):
        append_claim(layout, _stub_claim(claim_id=f"clm-2026-{i:06d}", tags=["safety"]))
    results = query_claims(ClaimFilter(tags=["finality"]), ws)
    assert len(results) == 3


def test_query_claims_filter_by_state(tmp_path):
    ws = _make_workspace(tmp_path)
    layout = WorkspaceLayout(ws)
    append_claim(layout, _stub_claim(claim_id="clm-2026-000001", status="proposed"))
    append_claim(layout, _stub_claim(claim_id="clm-2026-000002", status="proposed"))
    results = query_claims(ClaimFilter(state="proposed"), ws)
    assert len(results) == 2
    results_verified = query_claims(ClaimFilter(state="verified"), ws)
    assert len(results_verified) == 0


def test_query_claims_filter_by_source_ids(tmp_path):
    ws = _make_workspace(tmp_path)
    layout = WorkspaceLayout(ws)
    append_claim(layout, _stub_claim(claim_id="clm-2026-000001"))
    results = query_claims(ClaimFilter(source_ids=["small"]), ws)
    assert len(results) == 1
    results_none = query_claims(ClaimFilter(source_ids=["nonexistent"]), ws)
    assert len(results_none) == 0


def test_query_claims_record_fields(tmp_path):
    ws = _make_workspace(tmp_path)
    layout = WorkspaceLayout(ws)
    append_claim(layout, _stub_claim())
    records = query_claims(ClaimFilter(), ws)
    r = records[0]
    assert r.id == "clm-2026-000001"
    assert r.state == "proposed"
    assert isinstance(r.tags, list)
    assert r.source_id == "small"
    assert r.body != ""
    assert r.locator != ""


# ---------------------------------------------------------------------------
# IF-BK-3: is_source_ingested
# ---------------------------------------------------------------------------

def test_is_source_ingested_false_for_unknown(tmp_path):
    ws = _make_workspace(tmp_path)
    assert is_source_ingested("aabbcc" * 10, ws) is False


def test_is_source_ingested_true_after_ingest(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ingest_pdf(SMALL_PDF, ws)
    assert is_source_ingested(result.sha256, ws) is True


# ---------------------------------------------------------------------------
# IF-BK-4: list_concepts
# ---------------------------------------------------------------------------

def test_list_concepts_empty_workspace(tmp_path):
    ws = _make_workspace(tmp_path)
    concepts = list_concepts(ws)
    assert concepts == []


def test_list_concepts_returns_concept_refs(tmp_path):
    ws = _make_workspace(tmp_path)
    concepts_dir = ws / "wiki" / "concepts"
    # Write two minimal concept pages
    (concepts_dir / "finality.md").write_text(
        "---\ntitle: Finality\nsources: [small]\nsurface_forms: [finality, final]\n---\nSome content.\n",
        encoding="utf-8",
    )
    (concepts_dir / "safety.md").write_text(
        "---\ntitle: Safety\nsources: []\nsurface_forms: []\n---\n",
        encoding="utf-8",
    )
    concepts = list_concepts(ws)
    assert len(concepts) == 2
    slugs = {c.slug for c in concepts}
    assert "finality" in slugs
    assert "safety" in slugs
    for c in concepts:
        assert isinstance(c, ConceptRef)
        assert c.slug != ""
        assert c.title != ""
