"""Tests for the ingest-trace -> ledger-row projection.

REQ-TRACE-001: trace_to_ledger projects claim/verified events to ledger rows.
REQ-TRACE-002: non-verified heads are dropped.
REQ-TRACE-003: text backfilled from preceding claim/proposed event.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from scripts._edn_reader import Keyword, Symbol
from scripts._edn_writer import write_edn
from scripts.trace_to_ledger import (
    project_trace_to_ledger_rows,
    read_trace,
    TraceProjectionError,
)


def _write_trace(path: Path, events: list[tuple[Symbol, dict]]) -> None:
    payload = {
        Keyword("version"): 1,
        Keyword("book/id"): "test-ws",
        Keyword("events"): [[head, body] for head, body in events],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(write_edn(payload, pretty=True) + "\n", encoding="utf-8")


def test_project_verified_event_to_ledger_row(tmp_path: Path) -> None:
    trace = tmp_path / "trace.edn"
    instant = dt.datetime(2026, 5, 12, 16, 14, 1, tzinfo=dt.timezone.utc)
    _write_trace(trace, [
        (Symbol("verified", namespace="claim"), {
            Keyword("claim/id"): "clm-2026-000001",
            Keyword("text"): "Bermuda has nine traditional parishes.",
            Keyword("transitioned-at"): instant,
            Keyword("from"): Keyword("proposed"),
            Keyword("to"): Keyword("verified"),
        }),
    ])
    rows = project_trace_to_ledger_rows(read_trace(trace))
    assert len(rows) == 1
    row = rows[0]
    assert row["claim_id"] == "clm-2026-000001"
    assert row["status"] == "verified"
    assert row["canonical_text"] == "Bermuda has nine traditional parishes."
    assert row["confidence"] >= 0.0


def test_project_skips_non_verified_heads(tmp_path: Path) -> None:
    trace = tmp_path / "trace.edn"
    _write_trace(trace, [
        (Symbol("ingested", namespace="source"), {Keyword("doc/id"): "alpha"}),
        (Symbol("proposed", namespace="claim"), {Keyword("claim/id"): "clm-x"}),
        (Symbol("disputed", namespace="claim"), {Keyword("claim/id"): "clm-y"}),
    ])
    assert project_trace_to_ledger_rows(read_trace(trace)) == []


def test_project_picks_text_from_proposed_when_verified_lacks_it(tmp_path: Path) -> None:
    trace = tmp_path / "trace.edn"
    _write_trace(trace, [
        (Symbol("proposed", namespace="claim"), {
            Keyword("claim/id"): "clm-2026-000007",
            Keyword("text"): "Bermuda has nine traditional parishes.",
            Keyword("confidence"): 0.92,
        }),
        (Symbol("verified", namespace="claim"), {
            Keyword("claim/id"): "clm-2026-000007",
            Keyword("from"): Keyword("proposed"),
            Keyword("to"): Keyword("verified"),
        }),
    ])
    rows = project_trace_to_ledger_rows(read_trace(trace))
    assert len(rows) == 1
    assert rows[0]["claim_id"] == "clm-2026-000007"
    assert rows[0]["canonical_text"] == "Bermuda has nine traditional parishes."
    assert rows[0]["confidence"] == 0.92
    assert rows[0]["status"] == "verified"


def test_read_trace_returns_structure(tmp_path: Path) -> None:
    trace = tmp_path / "trace.edn"
    _write_trace(trace, [
        (Symbol("ingested", namespace="source"), {Keyword("doc/id"): "alpha"}),
    ])
    data = read_trace(trace)
    assert data["version"] == 1
    assert data["book_id"] == "test-ws"
    assert len(data["events"]) == 1
    assert data["events"][0]["head"] == "source/ingested"


def test_read_trace_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(TraceProjectionError, match="not found"):
        read_trace(tmp_path / "absent.edn")
