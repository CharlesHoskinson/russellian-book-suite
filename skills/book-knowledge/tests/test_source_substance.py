"""Thin-source guard: flag claims whose source is a stub with no real body."""
from datetime import datetime, timezone
from pathlib import Path

from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ledger import append_claim
from scripts.ingest_markdown import ingest_markdown
from scripts.verify_claim import verify_claim
from scripts.source_substance import (
    source_body, body_chars, find_thin_sourced_claims, MIN_SOURCE_BODY_CHARS,
)


def test_source_body_strips_frontmatter():
    text = "---\ntitle: T\nurl: u\n---\n\nReal body sentence here.\n"
    assert source_body(text) == "Real body sentence here."
    assert body_chars(text) == len("Real body sentence here.")


def test_source_body_without_frontmatter_is_unchanged():
    text = "# Heading\n\nA paragraph of real content.\n"
    assert "A paragraph of real content." in source_body(text)


def _claim(locator: str, doc_id: str, cid: str = "clm-2026-000001") -> dict:
    return {
        "claim_id": cid,
        "canonical_text": "placeholder claim text",
        "status": "proposed",
        "claim_type": "fact",
        "confidence": 0.8,
        "source_spans": [{"doc_id": doc_id, "locator_text": locator}],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def test_find_thin_sourced_claims_flags_stub(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    layout = WorkspaceLayout(workspace)
    m = ingest_markdown(Path("tests/fixtures/stub_source.md"), workspace)
    # The locator phrase lives only in the stub's frontmatter title.
    append_claim(layout, _claim("validation is the central challenge", m["doc_id"]))
    flagged = find_thin_sourced_claims(layout)
    assert len(flagged) == 1
    assert flagged[0]["claim_id"] == "clm-2026-000001"
    assert flagged[0]["reason"] == "thin source body"
    assert flagged[0]["body_chars"] < MIN_SOURCE_BODY_CHARS


def test_find_thin_sourced_claims_clean_for_real_source(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    layout = WorkspaceLayout(workspace)
    m = ingest_markdown(Path("tests/fixtures/small.md"), workspace)
    append_claim(layout, _claim("three components", m["doc_id"]))
    assert find_thin_sourced_claims(layout) == []


def test_verify_warns_but_promotes_on_thin_source(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    layout = WorkspaceLayout(workspace)
    m = ingest_markdown(Path("tests/fixtures/stub_source.md"), workspace)
    append_claim(layout, _claim("validation is the central challenge", m["doc_id"]))
    result = verify_claim(layout, "clm-2026-000001")
    # The locator is present (in frontmatter), so the claim still verifies...
    assert result.ok is True
    assert result.new_status == "verified"
    # ...but the thin source is surfaced as a warning.
    assert result.warnings
    assert "thin source" in result.warnings[0]


def test_verify_no_warning_on_real_source(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    layout = WorkspaceLayout(workspace)
    m = ingest_markdown(Path("tests/fixtures/small.md"), workspace)
    append_claim(layout, _claim("three components", m["doc_id"]))
    result = verify_claim(layout, "clm-2026-000001")
    assert result.ok is True
    assert result.warnings == ()
