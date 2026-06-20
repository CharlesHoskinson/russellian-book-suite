"""Live chapter drafting consumes S1 retrieval bundles (REQ-DRAFT-001..006)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

def _bundle(*, rebuttals: list[dict] | None = None, unanchored: bool = False) -> dict:
    payload = {
        "schema": "chapter-retrieval-bundle/v1",
        "chapter-id": "ch-01",
        "chapter-uri": "https://example.org/book-knowledge/chapters/ch-01",
        "dominant-communities": [
            {
                "rank": 1,
                "community-id": "comm-navigation",
                "claim-count": 2,
                "claim-ids": ["clm-2026-000002", "clm-2026-000001"],
            }
        ],
        "load-bearing-claims": [
            {
                "claim-id": "clm-2026-000002",
                "text": "Second claim should appear first by bundle order.",
                "status": "verified",
                "confidence": 0.95,
                "source-span-ids": ["span-b"],
            },
            {
                "claim-id": "clm-2026-000001",
                "text": "First claim should appear second by bundle order.",
                "status": "verified",
                "confidence": 0.90,
                "source-span-ids": ["span-a"],
            },
            {
                "claim-id": "clm-2026-000003",
                "text": "Unanchored claim must not be assertable.",
                "status": "verified",
                "confidence": 0.80,
                "source-span-ids": [],
            },
        ],
        "unresolved-rebuttals": rebuttals
        if rebuttals is not None
        else [
            {
                "counter-claim-id": "cc-2026-open01",
                "target-claim-id": "clm-2026-000001",
                "status": "open",
                "created-at": "2026-06-18T00:00:00+00:00",
            }
        ],
        "source-span-anchors": [
            {
                "span-id": "span-b",
                "claim-id": "clm-2026-000002",
                "doc-id": "doc-b",
                "node-id": "node-b",
                "page-index": 7,
                "locator-text": "page 7",
            },
            {
                "span-id": "span-a",
                "claim-id": "clm-2026-000001",
                "doc-id": "doc-a",
                "node-id": "node-a",
                "page-index": 3,
                "locator-text": "page 3",
            },
        ],
    }
    if unanchored:
        payload["flags"] = {
            "unanchored-load-bearing": [
                {"claim-id": "clm-2026-000003", "reason": "no-source-span"}
            ]
        }
    return {
        "chapter_id": "ch-01",
        "payload": payload,
        "json": json.dumps(payload, indent=2, sort_keys=True) + "\n",
        "edn": "{:schema \"chapter-retrieval-bundle/v1\"}\n",
        "prompt_scaffold": "Thesis cue: state the chapter thesis from the retrieval bundle.",
    }


def _seed_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "book"
    (workspace / "claims").mkdir(parents=True)
    (workspace / "claims" / "ledger.jsonl").write_text(
        json.dumps({"claim_id": "clm-2026-000001", "status": "verified"}) + "\n",
        encoding="utf-8",
    )
    return workspace


def test_scaffold_built_from_bundle(monkeypatch, tmp_path: Path) -> None:
    """REQ-DRAFT-001: the live draft path uses the bundle, not a flat claim list."""
    from scripts import draft_chapter, query_chapter_evidence

    workspace = _seed_workspace(tmp_path)
    calls: list[tuple[Path, str]] = []

    def fake_bundle(workspace_arg: Path, chapter_id: str) -> dict:
        calls.append((Path(workspace_arg), chapter_id))
        return _bundle()

    def flat_list_forbidden(*_args, **_kwargs) -> dict:
        raise AssertionError("flat verified-claim list must not scaffold drafting")

    monkeypatch.setattr(draft_chapter.chapter_bundle, "build_chapter_bundle_input", fake_bundle)
    monkeypatch.setattr(query_chapter_evidence, "query_chapter_evidence", flat_list_forbidden)

    result = draft_chapter.draft_chapter(
        workspace,
        "ch-01",
        llm_call=lambda prompt: "Draft body from bundle.",
    )

    assert calls == [(workspace, "ch-01")]
    assert "Second claim should appear first" in result.prompt
    assert "flat" not in result.prompt.lower()
    assert (workspace / "chapters" / "drafts" / "ch-01" / "draft.md").read_text(
        encoding="utf-8"
    ) == "Draft body from bundle.\n"


def test_prompt_follows_bundle_scaffold(monkeypatch, tmp_path: Path) -> None:
    """REQ-DRAFT-002: prompt uses the bundle scaffold and payload sections."""
    from scripts import draft_chapter

    workspace = _seed_workspace(tmp_path)
    monkeypatch.setattr(
        draft_chapter.chapter_bundle,
        "build_chapter_bundle_input",
        lambda *_args: _bundle(),
    )

    prompts: list[str] = []
    draft_chapter.draft_chapter(
        workspace,
        "ch-01",
        llm_call=lambda prompt: prompts.append(prompt) or "Draft body.",
    )

    prompt = prompts[0]
    assert "Thesis cue: state the chapter thesis from the retrieval bundle." in prompt
    assert "Support claims" in prompt
    assert "clm-2026-000002" in prompt
    assert "span-b" in prompt
    assert "Caveats" in prompt
    assert "cc-2026-open01 targets clm-2026-000001" in prompt


def test_bundle_access_read_only(monkeypatch, tmp_path: Path) -> None:
    """REQ-DRAFT-003: bundle access leaves the ledger unchanged and writes chapters only."""
    from scripts import draft_chapter

    workspace = _seed_workspace(tmp_path)
    before = (workspace / "claims" / "ledger.jsonl").read_bytes()
    loaded: list[str] = []

    def fake_loader(name: str):
        loaded.append(name)
        assert name == "project_chapter_bundle"
        bundle = _bundle()
        return SimpleNamespace(
            project_chapter_bundle=lambda workspace_arg, chapter_id: {
                "payload": bundle["payload"],
                "payload_json": bundle["json"],
                "payload_edn": bundle["edn"],
                "prompt_scaffold": bundle["prompt_scaffold"],
            },
            validate_bundle_payload=lambda _payload: None,
        )

    monkeypatch.setattr(draft_chapter.chapter_bundle, "load_book_knowledge_module", fake_loader)

    draft_chapter.draft_chapter(
        workspace,
        "ch-01",
        llm_call=lambda _prompt: "Draft body.",
    )

    assert loaded == ["project_chapter_bundle"]
    assert (workspace / "claims" / "ledger.jsonl").read_bytes() == before
    written_files = sorted(
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    )
    assert written_files == [
        "chapters/drafts/ch-01/blocked-paragraphs.json",
        "chapters/drafts/ch-01/draft-prompt.md",
        "chapters/drafts/ch-01/draft-scaffold.json",
        "chapters/drafts/ch-01/draft.md",
        "chapters/drafts/ch-01/writer-assertions.jsonl",
        "claims/ledger.jsonl",
    ]


def test_claims_presented_with_anchors_in_order() -> None:
    """REQ-DRAFT-004: claims are in bundle order and paired with anchors."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    scaffold = build_bundle_scaffold(_bundle(unanchored=True))
    prompt = render_drafting_prompt(scaffold)

    assert [item["claim-id"] for item in scaffold["support-claims"]] == [
        "clm-2026-000002",
        "clm-2026-000001",
    ]
    assert scaffold["support-claims"][0]["anchor"]["span-id"] == "span-b"
    assert scaffold["support-claims"][1]["anchor"]["span-id"] == "span-a"
    assert "Unanchored claim must not be assertable" not in prompt
    assert scaffold["flags"]["unanchored-load-bearing"][0]["claim-id"] == "clm-2026-000003"


def test_open_rebuttal_caveated() -> None:
    """REQ-DRAFT-005: open rebuttals become caveats and absent rebuttals do not."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    with_rebuttal = render_drafting_prompt(build_bundle_scaffold(_bundle()))
    without_rebuttal = render_drafting_prompt(
        build_bundle_scaffold(_bundle(rebuttals=[]))
    )

    assert "cc-2026-open01 targets clm-2026-000001" in with_rebuttal
    assert "Caveats" not in without_rebuttal
    assert "cc-2026-open01" not in without_rebuttal


def test_unanchored_claim_not_assertable() -> None:
    """REQ-DRAFT-006: unanchored load-bearing claims are withheld and flagged."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    scaffold = build_bundle_scaffold(_bundle(unanchored=True))
    prompt = render_drafting_prompt(scaffold)

    assert "clm-2026-000003" not in [
        item["claim-id"] for item in scaffold["support-claims"]
    ]
    assert scaffold["flags"]["unanchored-load-bearing"][0]["claim-id"] == "clm-2026-000003"
    assert "Do not assert unanchored load-bearing claims" in prompt
    assert "Unanchored claim must not be assertable" not in prompt
