# skills/book-knowledge/tests/test_export_symbolic_trace.py
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import datetime as dt
import json
from pathlib import Path


# scripts/__init__.py extends the package path to include neurosym-forge's
# scripts/, so the imports below resolve to the correct forge modules.
from scripts._edn_reader import Keyword, Symbol, read_edn  # noqa: E402

from scripts.export_symbolic_trace import export_trace, _manifest_to_event, _claim_to_proposed_event


def _seed_workspace(root: Path) -> Path:
    workspace = root / "ws"
    (workspace / "raw" / "manifests").mkdir(parents=True)
    (workspace / "claims").mkdir()
    (workspace / "raw" / "manifests" / "alpha.json").write_text(json.dumps({
        "doc_name": "alpha.pdf",
        "doc_id": "alpha",
        "source_kind": "pdf",
        "sha256": "a" * 64,
        "byte_size": 123,
        "ingested_at": "2026-05-12T16:13:51.630442Z",
        "node_count": 3,
        "trust": 0.95,
    }), encoding="utf-8")
    (workspace / "claims" / "ledger.jsonl").write_text(
        json.dumps({
            "claim_id": "clm-2026-000001",
            "canonical_text": "Bermuda has nine traditional parishes including St. George's.",
            "status": "verified",
            "confidence": 0.95,
            "created_at": "2026-05-12T16:14:01Z",
            "source_spans": [{"doc_id": "alpha", "locator_text": "Bermuda has nine traditional parishes"}],
        }) + "\n",
        encoding="utf-8",
    )
    return workspace


def test_manifest_event_shape(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    manifest = json.loads((workspace / "raw" / "manifests" / "alpha.json").read_text())
    head, payload = _manifest_to_event(manifest)
    assert head == Symbol("ingested", namespace="source")
    assert payload[Keyword("doc/id")] == "alpha"
    assert isinstance(payload[Keyword("ingested-at")], dt.datetime)
    # kind is derived from the manifest's authoritative source_kind field,
    # not from an absent path key (which the manifest schema forbids).
    assert payload[Keyword("kind")] == Keyword("pdf")


def test_markdown_manifest_infers_markdown_kind() -> None:
    head, payload = _manifest_to_event({
        "doc_name": "beta.md",
        "doc_id": "beta",
        "source_kind": "markdown",
        "sha256": "b" * 64,
        "ingested_at": "2026-05-12T16:13:51Z",
        "node_count": 1,
    })
    assert payload[Keyword("kind")] == Keyword("markdown")


def test_claim_event_shape() -> None:
    claim = {
        "claim_id": "clm-2026-000001",
        "canonical_text": "x",
        "status": "verified",
        "confidence": 0.9,
        "created_at": "2026-05-12T16:14:01Z",
        "source_spans": [],
    }
    head, payload = _claim_to_proposed_event(claim)
    assert head == Symbol("proposed", namespace="claim")
    assert payload[Keyword("claim/id")] == "clm-2026-000001"
    assert payload[Keyword("confidence")] == 0.9


def test_export_writes_edn_trace(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    out = workspace / "analysis" / "ingest-trace.edn"
    export_trace(workspace, out)
    text = out.read_text(encoding="utf-8")
    parsed = read_edn(text)
    assert parsed[Keyword("version")] == 1
    assert parsed[Keyword("book/id")] == "ws"
    events = parsed[Keyword("events")]
    assert len(events) == 2  # one source/ingested + one claim/proposed
    heads = [e[0] for e in events]
    assert Symbol("ingested", namespace="source") in heads
    assert Symbol("proposed", namespace="claim") in heads


def test_export_idempotent(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    out = workspace / "analysis" / "ingest-trace.edn"
    export_trace(workspace, out)
    first = out.read_text(encoding="utf-8")
    export_trace(workspace, out)
    second = out.read_text(encoding="utf-8")
    assert first == second


def test_export_skips_corrupt_ledger_line(tmp_path: Path) -> None:
    """4.2: a malformed ledger line is skipped (read_jsonl), not fatal."""
    workspace = _seed_workspace(tmp_path)
    with (workspace / "claims" / "ledger.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("{ this is not valid json\n")
    out = tmp_path / "trace.edn"
    count = export_trace(workspace, out)  # must not raise
    assert count >= 1
    assert out.exists()


def test_export_skips_corrupt_manifest(tmp_path: Path) -> None:
    """4.2: a malformed manifest JSON is skipped, not fatal."""
    workspace = _seed_workspace(tmp_path)
    (workspace / "raw" / "manifests" / "bad.json").write_text("{ broken", encoding="utf-8")
    out = tmp_path / "trace.edn"
    count = export_trace(workspace, out)  # must not raise
    assert count >= 1
