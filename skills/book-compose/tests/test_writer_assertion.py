"""Tests for the S2 writer assertion contract (REQ-ATTR-001..008)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from scripts.sibling_skills import load_book_knowledge_module
from scripts.writer_assertion import (
    WriterAssertionError,
    check_writer_assertion,
    decompose_paragraph,
    evaluate_paragraph_publication,
    read_writer_assertions,
    record_generated_sentence,
    record_writer_assertion,
    resolve_for_publication,
)


def _workspace(tmp_path: Path) -> Path:
    workspace_mod = load_book_knowledge_module("workspace")
    return workspace_mod.init_workspace(tmp_path / "book")


def _book_qa_writer():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "book-qa"
        / "scripts"
        / "attributed_generation_writeback.py"
    )
    spec = importlib.util.spec_from_file_location("_book_qa_attr_writeback", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_book_qa_attr_writeback"] = module
    spec.loader.exec_module(module)
    return module.write_novel_draft_claim_proposals


def _assertion(sentence: str = "The cited source says the daemon wakes.") -> dict:
    return {
        "id": "wa-ch-01-p001-0001",
        "chapter_id": "ch-01",
        "paragraph_id": "p001",
        "sentence_index": 1,
        "sentence_text": sentence,
        "asserts_claim": ["clm-2026-000001"],
        "cites_span": ["span-0001"],
        "citation_check_status": None,
        "revision_origin": None,
        "published_text": None,
        "flags": [],
    }


def test_assertion_binds_claim_and_span(tmp_path: Path) -> None:
    """REQ-ATTR-001: writer assertions reject empty claim/span bindings."""
    workspace = _workspace(tmp_path)
    record = record_writer_assertion(
        workspace,
        chapter_id="ch-01",
        paragraph_id="p001",
        sentence_index=1,
        sentence_text="The daemon wakes when the queue has work.",
        asserts_claim=["clm-2026-000001"],
        cites_span=["span-0001"],
    )

    assert record["asserts_claim"] == ["clm-2026-000001"]
    assert record["cites_span"] == ["span-0001"]

    with pytest.raises(WriterAssertionError, match="asserts_claim"):
        record_writer_assertion(
            workspace,
            chapter_id="ch-01",
            paragraph_id="p001",
            sentence_index=2,
            sentence_text="Unbound claim.",
            asserts_claim=[],
            cites_span=["span-0001"],
        )
    with pytest.raises(WriterAssertionError, match="cites_span"):
        record_writer_assertion(
            workspace,
            chapter_id="ch-01",
            paragraph_id="p001",
            sentence_index=3,
            sentence_text="Unbound span.",
            asserts_claim=["clm-2026-000001"],
            cites_span=[],
        )

    assert len(read_writer_assertions(workspace, "ch-01")) == 1


def test_generation_records_assertion(tmp_path: Path) -> None:
    """REQ-ATTR-002: generation materializes exactly one writer assertion."""
    workspace = _workspace(tmp_path)

    record_generated_sentence(
        workspace,
        chapter_id="ch-01",
        paragraph_id="p001",
        sentence_index=1,
        sentence_text="The queue wakes the daemon.",
        asserts_claim=["clm-2026-000001"],
        cites_span=["span-0001"],
    )

    rows = read_writer_assertions(workspace, "ch-01")
    assert len(rows) == 1
    assert rows[0]["sentence_text"] == "The queue wakes the daemon."
    assert rows[0]["asserts_claim"] == ["clm-2026-000001"]
    assert rows[0]["cites_span"] == ["span-0001"]
    assert (
        workspace / "chapters" / "drafts" / "ch-01" / "writer-assertions.jsonl"
    ).is_file()


def test_citation_check_sets_status() -> None:
    """REQ-ATTR-003: citation checks set exactly full/partial/none."""
    spans = {"span-0001": "The cited source says the daemon wakes when work arrives."}

    def fake_llm(prompt: str) -> str:
        if "contradicts" in prompt:
            return "none"
        return "full"

    full = check_writer_assertion(
        _assertion("The cited source says the daemon wakes when work arrives."),
        spans,
        llm_call=fake_llm,
    )
    none = check_writer_assertion(
        _assertion("This sentence contradicts the cited source."),
        spans,
        llm_call=fake_llm,
    )

    assert full["citation_check_status"] == "full"
    assert none["citation_check_status"] == "none"
    assert full["citation_check_status"] in {"full", "partial", "none"}
    assert none["citation_check_status"] in {"full", "partial", "none"}


def test_weak_support_revises_or_downgrades() -> None:
    """REQ-ATTR-004: weak support never publishes the original unchanged."""
    spans = {"span-0001": "The cited span reports an association."}
    original = "The cited span proves a cure."

    def check_revised(prompt: str) -> str:
        sentence_line = [
            line for line in prompt.splitlines() if line.startswith("Sentence:")
        ][0]
        if "The cited span reports an association." in sentence_line:
            return "full"
        return "none"

    revised = resolve_for_publication(
        _assertion(original),
        spans,
        llm_call=check_revised,
        revise_call=lambda sentence, span_text: "The cited span reports an association.",
    )
    assert revised["published_text"] == "The cited span reports an association."
    assert revised["published_text"] != original
    assert revised["revision_origin"]["action"] == "revised-from-span"

    downgraded = resolve_for_publication(
        _assertion(original),
        spans,
        llm_call=lambda prompt: "partial",
        revise_call=lambda sentence, span_text: sentence,
    )
    assert downgraded["published_text"] != original
    assert "partial-support" in downgraded["flags"]
    assert downgraded["revision_origin"]["action"] == "downgraded-partial-support"


def test_revision_origin_audit_trail() -> None:
    """REQ-ATTR-005: revision-origin records trigger status and action."""
    spans = {"span-0001": "The cited source says the daemon wakes."}

    full = resolve_for_publication(
        _assertion("The cited source says the daemon wakes."),
        spans,
        llm_call=lambda prompt: "full",
        revise_call=lambda sentence, span_text: "unused",
    )
    assert full["revision_origin"] == {
        "trigger_status": "full",
        "action": "unrevised",
    }

    revised = resolve_for_publication(
        _assertion("Unsupported original."),
        spans,
        llm_call=lambda prompt: "full" if "Supported rewrite." in prompt else "none",
        revise_call=lambda sentence, span_text: "Supported rewrite.",
    )
    assert revised["revision_origin"] == {
        "trigger_status": "none",
        "action": "revised-from-span",
    }

    downgraded = resolve_for_publication(
        _assertion("Weak original."),
        spans,
        llm_call=lambda prompt: "partial",
        revise_call=lambda sentence, span_text: sentence,
    )
    assert downgraded["revision_origin"] == {
        "trigger_status": "partial",
        "action": "downgraded-partial-support",
    }


def test_atomic_fact_maps_to_claim_or_novel() -> None:
    """REQ-ATTR-006: every atomic fact maps to a claim or novel draft claim."""
    known_claims = {
        "clm-2026-000001": "The daemon wakes when work arrives.",
    }

    def fake_decomposer(prompt: str) -> str:
        return json.dumps(
            [
                {
                    "text": "The daemon wakes when work arrives.",
                    "claim_id": "clm-2026-000001",
                },
                {"text": "The daemon also rewrites the scheduler."},
            ]
        )

    facts = decompose_paragraph(
        "The daemon wakes when work arrives. It also rewrites the scheduler.",
        known_claims,
        llm_call=fake_decomposer,
        chapter_id="ch-01",
        paragraph_id="p001",
    )

    assert facts[0]["claim_id"] == "clm-2026-000001"
    assert facts[0]["novel_draft_claim"] is None
    assert facts[1]["claim_id"] is None
    assert facts[1]["novel_draft_claim"].startswith("novel-")
    assert all(f["claim_id"] or f["novel_draft_claim"] for f in facts)


def test_novel_draft_claim_blocks_publication(tmp_path: Path) -> None:
    """REQ-ATTR-007: novel draft claims block and route QA proposals."""
    workspace = _workspace(tmp_path)
    before = (workspace / "claims" / "ledger.jsonl").read_bytes()
    facts = [
        {
            "id": "fact-ch-01-p001-0001",
            "chapter_id": "ch-01",
            "paragraph_id": "p001",
            "text": "The daemon rewrites the scheduler.",
            "claim_id": None,
            "novel_draft_claim": "novel-abc123",
        }
    ]

    result = evaluate_paragraph_publication(
        workspace,
        "ch-01",
        "p001",
        facts,
        proposal_writer=_book_qa_writer(),
    )

    assert result["passes"] is False
    assert result["blocked_by"] == ["novel-abc123"]
    assert (workspace / "claims" / "ledger.jsonl").read_bytes() == before
    assert not (workspace / "claims" / "proposed-transitions.jsonl").exists()
    proposal_path = workspace / "qa" / "proposed-transitions.jsonl"
    proposals = [
        json.loads(line)
        for line in proposal_path.read_text(encoding="utf-8").splitlines()
    ]
    assert proposals == [
        {
            "auto_apply": False,
            "chapter_id": "ch-01",
            "fact_id": "fact-ch-01-p001-0001",
            "kind": "novel_draft_claim",
            "novel_draft_claim": "novel-abc123",
            "paragraph_id": "p001",
            "requires": "human-review",
            "text": "The daemon rewrites the scheduler.",
        }
    ]

    ingested = [dict(facts[0], claim_id="clm-2026-000009", novel_draft_claim=None)]
    assert evaluate_paragraph_publication(workspace, "ch-01", "p001", ingested)["passes"]
    assert evaluate_paragraph_publication(workspace, "ch-01", "p001", [])["passes"]


def test_check_offline_and_deterministic() -> None:
    """REQ-ATTR-008: stubbed checks are offline and deterministic."""
    spans = {"span-0001": "The cited source says the daemon wakes."}
    prompts: list[str] = []

    class FakeLLM:
        network_calls = 0

        def __call__(self, prompt: str) -> str:
            prompts.append(prompt)
            return "partial"

    fake = FakeLLM()
    first = check_writer_assertion(_assertion(), spans, llm_call=fake)
    second = check_writer_assertion(_assertion(), spans, llm_call=fake)

    assert first["citation_check_status"] == "partial"
    assert second["citation_check_status"] == "partial"
    assert prompts[0] == prompts[1]
    assert fake.network_calls == 0
