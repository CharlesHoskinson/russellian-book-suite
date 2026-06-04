# skills/book-knowledge/tests/test_load_symbolic_trace.py
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import datetime as dt
from pathlib import Path

import pytest

# scripts/__init__.py extends the package path to include neurosym-forge's
# scripts/, so the imports below resolve to the correct forge modules.

from scripts.export_symbolic_trace import export_trace
from scripts.load_symbolic_trace import load_trace


def _seed_workspace(root: Path) -> Path:
    import json
    workspace = root / "ws"
    (workspace / "raw" / "manifests").mkdir(parents=True)
    (workspace / "claims").mkdir()
    (workspace / "raw" / "manifests" / "alpha.json").write_text(json.dumps({
        "doc_id": "alpha",
        "ingested_at": "2026-05-12T16:13:51.630442Z",
        "path": "raw/alpha.pdf",
        "title": "Alpha source",
    }), encoding="utf-8")
    (workspace / "claims" / "ledger.jsonl").write_text(
        json.dumps({
            "claim_id": "clm-2026-000001",
            "canonical_text": "x",
            "status": "verified",
            "confidence": 0.9,
            "created_at": "2026-05-12T16:14:01Z",
            "source_spans": [],
        }) + "\n",
        encoding="utf-8",
    )
    return workspace


def test_load_returns_structured_dict(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    out = workspace / "analysis" / "ingest-trace.edn"
    export_trace(workspace, out)
    loaded = load_trace(out)
    assert loaded["version"] == 1
    assert loaded["book_id"] == "ws"
    assert len(loaded["events"]) == 2
    e0 = loaded["events"][0]
    assert "head" in e0 and "payload" in e0
    assert e0["head"] == "source/ingested"


def test_loader_round_trip(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    out = workspace / "analysis" / "ingest-trace.edn"
    export_trace(workspace, out)
    loaded = load_trace(out)
    # The loaded events should round-trip through write+read
    assert all(isinstance(e["head"], str) for e in loaded["events"])
    for event in loaded["events"]:
        if event["head"] == "source/ingested":
            assert isinstance(event["payload"]["ingested-at"], dt.datetime)
        elif event["head"] == "claim/proposed":
            assert "claim/id" in event["payload"]


def test_loader_validates_schema(tmp_path: Path) -> None:
    # Write an invalid trace
    bad = tmp_path / "bad.edn"
    bad.write_text("{:version 2 :book/id \"x\" :events []}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"schema"):
        load_trace(bad)
