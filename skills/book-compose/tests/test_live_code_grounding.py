"""Live code-grounding scaffold tests (REQ-DRAFT-013..018)."""
from __future__ import annotations

import json
from pathlib import Path


def _bundle(
    *,
    code_links: dict[str, list[dict]] | None = None,
    evidence_only: list[dict] | None = None,
) -> dict:
    payload = {
        "schema": "chapter-retrieval-bundle/v1",
        "chapter-id": "ch-01",
        "chapter-uri": "https://example.org/book-knowledge/chapters/ch-01",
        "dominant-communities": [],
        "load-bearing-claims": [
            {
                "claim-id": "clm-2026-000101",
                "text": "The scheduler routes ready work through the daemon.",
                "status": "verified",
                "confidence": 0.95,
                "source-span-ids": ["span-101"],
            },
            {
                "claim-id": "clm-2026-000102",
                "text": "The reader surface remains detached from worker internals.",
                "status": "verified",
                "confidence": 0.91,
                "source-span-ids": ["span-102"],
            },
        ],
        "unresolved-rebuttals": [],
        "source-span-anchors": [
            {
                "span-id": "span-101",
                "claim-id": "clm-2026-000101",
                "doc-id": "doc-a",
                "node-id": "node-a",
                "page-index": 1,
                "locator-text": "The scheduler routes ready work.",
            },
            {
                "span-id": "span-102",
                "claim-id": "clm-2026-000102",
                "doc-id": "doc-b",
                "node-id": "node-b",
                "page-index": 2,
                "locator-text": "The reader surface is detached.",
            },
        ],
    }
    if code_links:
        payload["code-links"] = code_links
    if evidence_only:
        payload["link-evidence"] = evidence_only
    return {
        "chapter_id": "ch-01",
        "payload": payload,
        "json": json.dumps(payload, indent=2, sort_keys=True) + "\n",
        "edn": "{:schema \"chapter-retrieval-bundle/v1\"}\n",
        "prompt_scaffold": "Thesis cue: write from anchored claims.",
    }


def _canonical_links() -> dict[str, list[dict]]:
    return {
        "clm-2026-000101": [
            {
                "code-id": "scheduler_module",
                "code-label": "scheduler.py",
                "source-file": "src/scheduler.py",
                "link-kind": "file-path",
            }
        ],
        "clm-2026-000102": [
            {
                "code-id": "reader_surface",
                "code-label": "ReaderSurface",
                "source-file": "src/ui.py",
                "link-kind": "exact-symbol",
            }
        ],
    }


def test_software_chapter_surfaces_code_grounding() -> None:
    """REQ-DRAFT-013: software chapters surface canonical code links."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    scaffold = build_bundle_scaffold(_bundle(code_links=_canonical_links()))
    prompt = render_drafting_prompt(scaffold)

    assert scaffold["code-grounding"] == [
        {
            "claim-id": "clm-2026-000101",
            "code-id": "scheduler_module",
            "code-label": "scheduler.py",
            "source-file": "src/scheduler.py",
            "link-kind": "file-path",
        },
        {
            "claim-id": "clm-2026-000102",
            "code-id": "reader_surface",
            "code-label": "ReaderSurface",
            "source-file": "src/ui.py",
            "link-kind": "exact-symbol",
        },
    ]
    assert "Code grounding:" in prompt
    assert "clm-2026-000101 -> scheduler_module" in prompt


def test_only_canonical_links_surfaced() -> None:
    """REQ-DRAFT-014: ambiguous evidence-only candidates stay invisible."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    scaffold = build_bundle_scaffold(
        _bundle(
            code_links=_canonical_links(),
            evidence_only=[
                {
                    "claim-id": "clm-2026-000101",
                    "code-id": "ambiguous_worker",
                    "promoted": False,
                }
            ],
        )
    )
    prompt = render_drafting_prompt(scaffold)

    grounded_code_ids = {item["code-id"] for item in scaffold["code-grounding"]}
    assert grounded_code_ids == {"scheduler_module", "reader_surface"}
    assert "ambiguous_worker" not in grounded_code_ids
    assert "ambiguous_worker" not in prompt


def test_load_bearing_claim_paired_with_symbol() -> None:
    """REQ-DRAFT-015: each grounded load-bearing claim is paired with code."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    scaffold = build_bundle_scaffold(_bundle(code_links=_canonical_links()))
    prompt = render_drafting_prompt(scaffold)

    by_claim = {item["claim-id"]: item for item in scaffold["code-grounding"]}
    assert by_claim["clm-2026-000101"]["code-label"] == "scheduler.py"
    assert by_claim["clm-2026-000102"]["code-label"] == "ReaderSurface"
    assert "clm-2026-000102 -> reader_surface (ReaderSurface; src/ui.py; exact-symbol)" in prompt


def test_grounding_read_only_deterministic(tmp_path: Path) -> None:
    """REQ-DRAFT-016: grounding is read-only and deterministic over the bundle."""
    from scripts.draft_chapter import build_bundle_scaffold

    graph = tmp_path / "graphify-out" / "graph.json"
    ledger = tmp_path / "claims" / "ledger.jsonl"
    graph.parent.mkdir(parents=True)
    ledger.parent.mkdir(parents=True)
    graph.write_text('{"nodes":[],"links":[]}\n', encoding="utf-8")
    ledger.write_text('{"claim_id":"clm-2026-000101"}\n', encoding="utf-8")
    before_graph = graph.read_bytes()
    before_ledger = ledger.read_bytes()

    bundle = _bundle(code_links=_canonical_links())
    first = build_bundle_scaffold(bundle)
    second = build_bundle_scaffold(bundle)

    assert first["code-grounding"] == second["code-grounding"]
    assert graph.read_bytes() == before_graph
    assert ledger.read_bytes() == before_ledger


def test_evidence_only_claim_not_grounded() -> None:
    """REQ-DRAFT-017: claims with only evidence-only links are ungrounded."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    scaffold = build_bundle_scaffold(
        _bundle(
            evidence_only=[
                {
                    "claim-id": "clm-2026-000101",
                    "code-id": "maybe_scheduler",
                    "promoted": False,
                }
            ]
        )
    )
    prompt = render_drafting_prompt(scaffold)

    assert "code-grounding" not in scaffold
    assert "Code grounding:" not in prompt
    assert "maybe_scheduler" not in prompt


def test_non_software_chapter_omits_section() -> None:
    """REQ-DRAFT-018: chapters with no code links omit the grounding section."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    scaffold = build_bundle_scaffold(_bundle())
    prompt = render_drafting_prompt(scaffold)

    assert "code-grounding" not in scaffold
    assert "Code grounding:" not in prompt
