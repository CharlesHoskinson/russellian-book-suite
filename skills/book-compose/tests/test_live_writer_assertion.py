"""Live drafting applies the S2 writer-assertion contract (REQ-ATTR-009..014)."""
from __future__ import annotations

import json
from pathlib import Path


def _bundle() -> dict:
    payload = {
        "schema": "chapter-retrieval-bundle/v1",
        "chapter-id": "ch-01",
        "chapter-uri": "https://example.org/book-knowledge/chapters/ch-01",
        "dominant-communities": [],
        "load-bearing-claims": [
            {
                "claim-id": "clm-2026-000001",
                "text": "The daemon wakes when work arrives.",
                "status": "verified",
                "confidence": 0.95,
                "source-span-ids": ["span-0001"],
            },
            {
                "claim-id": "clm-2026-000002",
                "text": "The source reports an association.",
                "status": "verified",
                "confidence": 0.90,
                "source-span-ids": ["span-0002"],
            },
        ],
        "unresolved-rebuttals": [],
        "source-span-anchors": [
            {
                "span-id": "span-0001",
                "claim-id": "clm-2026-000001",
                "doc-id": "doc-a",
                "node-id": "node-a",
                "page-index": 1,
                "locator-text": "The source says the daemon wakes when work arrives.",
            },
            {
                "span-id": "span-0002",
                "claim-id": "clm-2026-000002",
                "doc-id": "doc-b",
                "node-id": "node-b",
                "page-index": 2,
                "locator-text": "The source reports an association, not proof.",
            },
        ],
    }
    return {
        "chapter_id": "ch-01",
        "payload": payload,
        "json": json.dumps(payload, indent=2, sort_keys=True) + "\n",
        "edn": "{:schema \"chapter-retrieval-bundle/v1\"}\n",
        "prompt_scaffold": "Thesis cue: write from anchored claims.",
    }


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "book"
    (workspace / "claims").mkdir(parents=True)
    (workspace / "claims" / "ledger.jsonl").write_text(
        json.dumps({"claim_id": "clm-2026-000001", "status": "verified"}) + "\n",
        encoding="utf-8",
    )
    return workspace


def _patch_bundle(monkeypatch) -> None:
    from scripts import draft_chapter

    monkeypatch.setattr(
        draft_chapter.chapter_bundle,
        "build_chapter_bundle_input",
        lambda *_args: _bundle(),
    )


def _draft_text() -> str:
    return "The daemon wakes when work arrives. Weak claim overstates the span."


def _faithfulness(prompt: str) -> str:
    if "Weak claim overstates the span." in prompt:
        return "partial"
    return "full"


def _decomposer_all_mapped(prompt: str) -> str:
    return json.dumps(
        [
            {
                "text": "The daemon wakes when work arrives.",
                "claim_id": "clm-2026-000001",
            }
        ]
    )


def _decomposer_with_novel(prompt: str) -> str:
    return json.dumps(
        [
            {
                "text": "The daemon wakes when work arrives.",
                "claim_id": "clm-2026-000001",
            },
            {"text": "The daemon rewrites the scheduler."},
        ]
    )


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_emitted_sentence_recorded_as_assertion(monkeypatch, tmp_path: Path) -> None:
    """REQ-ATTR-009: live emitted sentences are recorded with claim/span bindings."""
    from scripts import draft_chapter

    _patch_bundle(monkeypatch)
    workspace = _workspace(tmp_path)

    draft_chapter.draft_chapter(
        workspace,
        "ch-01",
        llm_call=lambda _prompt: _draft_text(),
        faithfulness_llm_call=_faithfulness,
        revise_call=lambda sentence, _span: sentence,
        decomposer_llm_call=_decomposer_all_mapped,
    )

    rows = _read_jsonl(workspace / "chapters" / "drafts" / "ch-01" / "writer-assertions.jsonl")
    assert len(rows) == 2
    assert rows[0]["sentence_text"] == "The daemon wakes when work arrives."
    assert rows[0]["asserts_claim"] == ["clm-2026-000001"]
    assert rows[0]["cites_span"] == ["span-0001"]
    assert rows[1]["asserts_claim"] == ["clm-2026-000002"]
    assert rows[1]["cites_span"] == ["span-0002"]


def test_faithfulness_check_sets_status(monkeypatch, tmp_path: Path) -> None:
    """REQ-ATTR-010: live assertions carry full/partial/none check statuses."""
    from scripts import draft_chapter

    _patch_bundle(monkeypatch)
    workspace = _workspace(tmp_path)

    draft_chapter.draft_chapter(
        workspace,
        "ch-01",
        llm_call=lambda _prompt: _draft_text(),
        faithfulness_llm_call=_faithfulness,
        revise_call=lambda sentence, _span: sentence,
        decomposer_llm_call=_decomposer_all_mapped,
    )

    rows = _read_jsonl(workspace / "chapters" / "drafts" / "ch-01" / "writer-assertions.jsonl")
    assert [row["citation_check_status"] for row in rows] == ["full", "partial"]
    assert all(row["citation_check_status"] in {"full", "partial", "none"} for row in rows)


def test_revise_or_downgrade_before_assembly(monkeypatch, tmp_path: Path) -> None:
    """REQ-ATTR-011: weak support is resolved before draft assembly."""
    from scripts import draft_chapter

    _patch_bundle(monkeypatch)
    workspace = _workspace(tmp_path)

    result = draft_chapter.draft_chapter(
        workspace,
        "ch-01",
        llm_call=lambda _prompt: _draft_text(),
        faithfulness_llm_call=_faithfulness,
        revise_call=lambda _sentence, _span: "The source reports an association.",
        decomposer_llm_call=_decomposer_all_mapped,
    )

    draft = result.draft_path.read_text(encoding="utf-8")
    assert "The daemon wakes when work arrives." in draft
    assert "Weak claim overstates the span." not in draft
    assert "The source reports an association." in draft
    rows = _read_jsonl(workspace / "chapters" / "drafts" / "ch-01" / "writer-assertions.jsonl")
    assert rows[1]["revision_origin"]["action"] == "revised-from-span"
    assert rows[1]["revision_origin"]["trigger_status"] == "partial"


def test_atomic_facts_mapped_to_claim_or_novel(monkeypatch, tmp_path: Path) -> None:
    """REQ-ATTR-012: live paragraph decomposition maps every atomic fact."""
    from scripts import draft_chapter

    _patch_bundle(monkeypatch)
    workspace = _workspace(tmp_path)

    draft_chapter.draft_chapter(
        workspace,
        "ch-01",
        llm_call=lambda _prompt: "The daemon wakes when work arrives.",
        faithfulness_llm_call=lambda _prompt: "full",
        revise_call=lambda sentence, _span: sentence,
        decomposer_llm_call=_decomposer_with_novel,
    )

    facts = _read_jsonl(workspace / "chapters" / "drafts" / "ch-01" / "draft-atomic-facts.jsonl")
    assert len(facts) == 2
    assert facts[0]["claim_id"] == "clm-2026-000001"
    assert facts[0]["novel_draft_claim"] is None
    assert facts[1]["claim_id"] is None
    assert facts[1]["novel_draft_claim"].startswith("novel-")
    assert all(fact["claim_id"] or fact["novel_draft_claim"] for fact in facts)


def test_novel_draft_claim_blocks_publication(monkeypatch, tmp_path: Path) -> None:
    """REQ-ATTR-013: novel draft claims block and route QA proposals."""
    from scripts import draft_chapter

    _patch_bundle(monkeypatch)
    workspace = _workspace(tmp_path)
    before = (workspace / "claims" / "ledger.jsonl").read_bytes()

    result = draft_chapter.draft_chapter(
        workspace,
        "ch-01",
        llm_call=lambda _prompt: "The daemon wakes when work arrives.",
        faithfulness_llm_call=lambda _prompt: "full",
        revise_call=lambda sentence, _span: sentence,
        decomposer_llm_call=_decomposer_with_novel,
    )

    assert result.draft_path.read_text(encoding="utf-8") == ""
    assert (workspace / "claims" / "ledger.jsonl").read_bytes() == before
    assert not (workspace / "claims" / "proposed-transitions.jsonl").exists()
    proposals = _read_jsonl(workspace / "qa" / "proposed-transitions.jsonl")
    assert proposals[0]["kind"] == "novel_draft_claim"
    assert proposals[0]["text"] == "The daemon rewrites the scheduler."

    clean_workspace = _workspace(tmp_path / "clean")
    draft_chapter.draft_chapter(
        clean_workspace,
        "ch-01",
        llm_call=lambda _prompt: "The daemon wakes when work arrives.",
        faithfulness_llm_call=lambda _prompt: "full",
        revise_call=lambda sentence, _span: sentence,
        decomposer_llm_call=_decomposer_all_mapped,
    )
    assert "The daemon wakes" in (
        clean_workspace / "chapters" / "drafts" / "ch-01" / "draft.md"
    ).read_text(encoding="utf-8")
    assert not (clean_workspace / "qa" / "proposed-transitions.jsonl").exists()


def test_faithfulness_and_decomposer_use_stub_seam(monkeypatch, tmp_path: Path) -> None:
    """REQ-ATTR-014: live model touchpoints are injected and stubbed."""
    from scripts import draft_chapter

    _patch_bundle(monkeypatch)
    workspace = _workspace(tmp_path)
    calls = {"generation": 0, "faithfulness": 0, "decomposer": 0}

    def fake_generation(_prompt: str) -> str:
        calls["generation"] += 1
        return "The daemon wakes when work arrives."

    def fake_faithfulness(_prompt: str) -> str:
        calls["faithfulness"] += 1
        return "full"

    def fake_decomposer(_prompt: str) -> str:
        calls["decomposer"] += 1
        return _decomposer_all_mapped(_prompt)

    draft_chapter.draft_chapter(
        workspace,
        "ch-01",
        llm_call=fake_generation,
        faithfulness_llm_call=fake_faithfulness,
        revise_call=lambda sentence, _span: sentence,
        decomposer_llm_call=fake_decomposer,
    )

    assert calls == {"generation": 1, "faithfulness": 1, "decomposer": 1}
