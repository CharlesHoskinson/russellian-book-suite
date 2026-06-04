import pytest

pytestmark = pytest.mark.windows_canary

import json
from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.project_graph import project_graph


def test_axiom_appears_in_graph(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "An axiom.",
        "status": "verified", "claim_type": "fact", "confidence": 0.9,
        "axiom": True,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-13T00:00:00Z",
    }) + "\n", encoding="utf-8")
    out = project_graph(layout)
    text = out.read_text(encoding="utf-8")
    assert "axiom" in text


def test_pin_low_confidence_appears_in_graph(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "A pinned low-confidence claim.",
        "status": "verified", "claim_type": "fact", "confidence": 0.3,
        "p_posterior": 0.3,
        "pin_low_confidence": True,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-13T00:00:00Z",
    }) + "\n", encoding="utf-8")
    out = project_graph(layout)
    text = out.read_text(encoding="utf-8")
    assert "pinLowConfidence" in text


def test_conflicts_with_appears_in_graph(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.ledger.write_text(
        json.dumps({
            "claim_id": "clm-2026-000001", "canonical_text": "Claim A.",
            "status": "verified", "claim_type": "fact", "confidence": 0.8,
            "conflicts_with": ["clm-2026-000002"],
            "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
            "created_at": "2026-05-13T00:00:00Z",
        }) + "\n" +
        json.dumps({
            "claim_id": "clm-2026-000002", "canonical_text": "Claim B contradicts A.",
            "status": "verified", "claim_type": "fact", "confidence": 0.8,
            "source_spans": [{"doc_id": "d", "locator_text": "efgh"}],
            "created_at": "2026-05-13T00:00:00Z",
        }) + "\n",
        encoding="utf-8")
    out = project_graph(layout)
    text = out.read_text(encoding="utf-8")
    assert "conflictsWith" in text


def test_p_posterior_appears_in_graph(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Hi.",
        "status": "verified", "claim_type": "fact", "confidence": 0.7,
        "p_posterior": 0.42,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
    }) + "\n", encoding="utf-8")
    out = project_graph(layout)
    text = out.read_text(encoding="utf-8")
    assert "pPosterior" in text or "0.42" in text


def test_counter_claim_rebuts_edge_appears(tmp_path):
    from scripts.counter_claims import append_counter_claim
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Hi.",
        "status": "verified", "claim_type": "fact", "confidence": 0.7,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
    }) + "\n", encoding="utf-8")
    append_counter_claim(tmp_path / "book", {
        "id": "cc-2026-abcdef", "target_claim_id": "clm-2026-000001",
        "text": "Rival hypothesis goes here.", "disagreement_vector": "scope",
        "status": "open",
        "provenance": {"generator": "abduction-v1", "prompt_sha256": "0" * 64},
        "created_at": "2026-05-11T00:00:00Z", "addressed_in_chapter": None,
    })
    out = project_graph(layout)
    text = out.read_text(encoding="utf-8")
    assert "rebuts" in text
    assert "cc-2026-abcdef" in text
