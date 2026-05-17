"""Phase-1 dispatch: ingest-trace preferred over ledger.jsonl when present.

REQ-TRACE-001: run_verification reads ingest-trace.edn when present.
REQ-TRACE-002: falls back to ledger.jsonl when trace is absent (legacy).
REQ-TRACE-004: trace preferred over legacy ledger when both present.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from scripts._edn_reader import Keyword, Symbol, read_edn
from scripts._edn_writer import write_edn
from scripts.run_verification import run


def _write_trace(workspace: Path, events: list[tuple[Symbol, dict]]) -> Path:
    out = workspace / "analysis" / "ingest-trace.edn"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        Keyword("version"): 1,
        Keyword("book/id"): workspace.name,
        Keyword("events"): [[head, body] for head, body in events],
    }
    out.write_text(write_edn(payload, pretty=True) + "\n", encoding="utf-8")
    return out


def _seed_workspace(tmp_path: Path, with_legacy_ledger: bool) -> Path:
    workspace = tmp_path / "examples" / "test-workspace"
    (workspace / "claims").mkdir(parents=True)
    if with_legacy_ledger:
        (workspace / "claims" / "ledger.jsonl").write_text(
            json.dumps({
                "claim_id": "clm-LEGACY-1",
                "claim_type": "fact",
                "canonical_text": "Legacy ledger claim.",
                "status": "verified",
                "confidence": 0.5,
            }) + "\n", encoding="utf-8"
        )
    (workspace / "qa").mkdir()
    return workspace


def test_run_verification_consumes_trace(tmp_path: Path, project_root: Path) -> None:
    """A 3-event trace with one verified claim -> run produces 1 atom in work/claims.edn."""
    workspace = _seed_workspace(tmp_path, with_legacy_ledger=False)
    instant = dt.datetime(2026, 5, 12, 16, 14, 1, tzinfo=dt.timezone.utc)
    _write_trace(workspace, [
        (Symbol("ingested", namespace="source"), {
            Keyword("doc/id"): "alpha",
            Keyword("ingested-at"): instant,
            Keyword("kind"): Keyword("pdf"),
        }),
        (Symbol("proposed", namespace="claim"), {
            Keyword("claim/id"): "clm-TRACE-1",
            Keyword("text"): "Bermuda has nine traditional parishes including St. George's.",
            Keyword("proposed-at"): instant,
            Keyword("confidence"): 0.9,
        }),
        (Symbol("verified", namespace="claim"), {
            Keyword("claim/id"): "clm-TRACE-1",
            Keyword("transitioned-at"): instant,
            Keyword("from"): Keyword("proposed"),
            Keyword("to"): Keyword("verified"),
        }),
    ])

    # Move into a tmp project_root so work/ is sandboxed
    sandbox_project = tmp_path / "project_root_clone"
    sandbox_project.mkdir()
    (sandbox_project / "rules").mkdir()
    # Copy only the predicates rules file we need
    (sandbox_project / "rules" / "predicates.edn").write_text(
        (project_root / "rules" / "predicates.edn").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rc = run(
        workspace=workspace,
        release_version="1.0.0",
        project_root=sandbox_project,
        stub_verifier=True,
        stub_verdict="sat",
    )
    assert rc == 0

    claims_edn = sandbox_project / "work" / "claims.edn"
    assert claims_edn.exists()
    parsed = read_edn(claims_edn.read_text(encoding="utf-8"))
    atoms = parsed[Keyword("atoms")]
    assert len(atoms) == 1
    assert atoms[0][Keyword("id")] == "clm-TRACE-1"


def test_run_verification_prefers_trace_over_legacy_ledger(
    tmp_path: Path, project_root: Path,
) -> None:
    """When BOTH are present, the trace wins."""
    workspace = _seed_workspace(tmp_path, with_legacy_ledger=True)
    _write_trace(workspace, [
        (Symbol("proposed", namespace="claim"), {
            Keyword("claim/id"): "clm-TRACE-2",
            Keyword("text"): "Bermuda has nine traditional parishes.",
            Keyword("confidence"): 0.95,
        }),
        (Symbol("verified", namespace="claim"), {
            Keyword("claim/id"): "clm-TRACE-2",
            Keyword("from"): Keyword("proposed"),
            Keyword("to"): Keyword("verified"),
        }),
    ])
    sandbox_project = tmp_path / "project_root_clone"
    sandbox_project.mkdir()
    (sandbox_project / "rules").mkdir()
    (sandbox_project / "rules" / "predicates.edn").write_text(
        (project_root / "rules" / "predicates.edn").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    rc = run(
        workspace=workspace, release_version="1.0.0",
        project_root=sandbox_project, stub_verifier=True, stub_verdict="sat",
    )
    assert rc == 0
    parsed = read_edn((sandbox_project / "work" / "claims.edn").read_text(encoding="utf-8"))
    atoms = parsed[Keyword("atoms")]
    ids = {a[Keyword("id")] for a in atoms}
    # Trace claim must appear; legacy claim must NOT
    assert "clm-TRACE-2" in ids
    assert "clm-LEGACY-1" not in ids


def test_run_verification_uses_legacy_ledger_when_no_trace(
    tmp_path: Path, project_root: Path,
) -> None:
    """No analysis/ingest-trace.edn -> falls back to claims/ledger.jsonl.

    REQ-TRACE-002: legacy fallback preserved when trace absent.
    """
    workspace = _seed_workspace(tmp_path, with_legacy_ledger=True)
    # NO trace file written.
    assert not (workspace / "analysis" / "ingest-trace.edn").exists()

    sandbox_project = tmp_path / "project_root_clone"
    sandbox_project.mkdir()
    (sandbox_project / "rules").mkdir()
    (sandbox_project / "rules" / "predicates.edn").write_text(
        (project_root / "rules" / "predicates.edn").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rc = run(
        workspace=workspace, release_version="1.0.0",
        project_root=sandbox_project, stub_verifier=True, stub_verdict="sat",
    )
    assert rc == 0
    parsed = read_edn((sandbox_project / "work" / "claims.edn").read_text(encoding="utf-8"))
    atoms = parsed[Keyword("atoms")]
    ids = {a[Keyword("id")] for a in atoms}
    assert "clm-LEGACY-1" in ids
    # No synthesised file should have been written either
    assert not (sandbox_project / "work" / "ledger-from-trace.jsonl").exists()


def test_run_verification_end_to_end_with_synth_trace_writes_qa(
    tmp_path: Path, project_root: Path,
) -> None:
    """Full Phase-1->4 run on a synth trace, with stubbed verifier, lands a
    verification-defects.json under qa/ with the expected verdict shape."""
    workspace = _seed_workspace(tmp_path, with_legacy_ledger=False)
    _write_trace(workspace, [
        (Symbol("ingested", namespace="source"), {Keyword("doc/id"): "alpha"}),
        (Symbol("proposed", namespace="claim"), {
            Keyword("claim/id"): "clm-E2E-1",
            Keyword("text"): "Bermuda has nine traditional parishes.",
            Keyword("confidence"): 0.99,
        }),
        (Symbol("verified", namespace="claim"), {
            Keyword("claim/id"): "clm-E2E-1",
            Keyword("from"): Keyword("proposed"),
            Keyword("to"): Keyword("verified"),
        }),
    ])
    sandbox_project = tmp_path / "project_root_clone"
    sandbox_project.mkdir()
    (sandbox_project / "rules").mkdir()
    (sandbox_project / "rules" / "predicates.edn").write_text(
        (project_root / "rules" / "predicates.edn").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rc = run(
        workspace=workspace, release_version="1.0.0",
        project_root=sandbox_project, stub_verifier=True, stub_verdict="sat",
    )
    assert rc == 0

    qa_out = workspace / "qa" / "verification-defects.json"
    assert qa_out.exists()
    payload = json.loads(qa_out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "sat"
    assert "core" in payload
    assert isinstance(payload["core"], list)
