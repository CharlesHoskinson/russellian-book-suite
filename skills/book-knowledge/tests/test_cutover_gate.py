"""P5.3 cutover gate (REQ-KG-010/018) — Cozo is the live default, clean on real data.

Locks the cutover invariants before the P5.4 deletion of the legacy stack:

- the DEFAULT backend (no ``KG_BACKEND`` flag) is **cozo** for BOTH dispatch points,
  ``validate_shacl`` and ``run_competency_queries`` — the defining property of the
  cutover (proven by spying that the rdflib code path is NOT taken);
- the real ``examples/bermuda-manual`` workspace is PRESENT — a HARD failure, not a
  skip (a skipped real-data leg is not proof — external-audit gate point 6);
- the default (cozo) pipeline runs clean end-to-end on bermuda: SHACL conforms and
  the competency gate completes, sourced from the ledger projection.

Coverage NOT duplicated here (already locked elsewhere): per-query golden parity
(``test_query_ports``), SHACL constraint parity incl. presence/datatype
(``test_constraint_ports`` / ``test_presence_ports``), the consistency pass + its
CLI/artifact contract and cross-skill alias safety (book-thesis
``test_consistency_cozo_parity`` / ``test_cross_skill_cozo_import``), and
``query_chapter_evidence`` quoting/superseded parity (book-compose
``test_query_chapter_evidence``).

The NO-LEGACY-IMPORT scan (no ``rdflib``/``pyshacl``/``pyDatalog`` imports) is a P5.4
gate — the imports are intentionally still present now so the cutover is revertable.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.windows_canary

from scripts.ledger import append_claim
from scripts.run_competency_queries import run_competency_queries
from scripts.workspace import WorkspaceLayout, init_workspace

ROOT = Path(__file__).resolve().parents[1]
BERMUDA = ROOT.parents[1] / "examples" / "bermuda-manual"


def _conforming_claim(claim_id: str) -> dict:
    return {
        "claim_id": claim_id,
        "canonical_text": "a well-formed verified claim",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "doc-1", "locator_text": "passage"}],
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def test_validate_shacl_is_cozo_only(tmp_path):
    """validate_shacl validates the LEDGER projection via Cozo and imports no pyshacl
    (the legacy rdflib SHACL path was deleted in P5.4a) — it conforms a clean ledger
    workspace with no TriG dataset projected."""
    import scripts.validate_shacl as vs

    assert "pyshacl" not in vs.__dict__, "validate_shacl must not import pyshacl"
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _conforming_claim("clm-2026-000001"))
    report = vs.validate_shacl(layout)
    assert report.conforms is True


def test_run_competency_defaults_to_cozo(tmp_path, monkeypatch):
    """No flag -> run_competency_queries does NOT load the RDF dataset (cozo path)."""
    import scripts.run_competency_queries as mod

    monkeypatch.delenv("KG_BACKEND", raising=False)
    called = {"rdflib": 0}
    real = mod._load_dataset

    def _spy(layout):
        called["rdflib"] += 1
        return real(layout)

    monkeypatch.setattr(mod, "_load_dataset", _spy)
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _conforming_claim("clm-2026-000001"))
    run_competency_queries(layout)
    assert called["rdflib"] == 0, "default backend must be cozo (no RDF dataset load)"


def test_bermuda_workspace_present_not_skipped():
    """Gate point 6: the real workspace MUST exist — a hard failure, never a skip."""
    assert BERMUDA.is_dir(), f"cutover gate requires the real workspace at {BERMUDA}"
    assert (BERMUDA / "claims" / "ledger.jsonl").is_file(), "bermuda ledger missing"


def test_default_cozo_pipeline_clean_on_bermuda(monkeypatch):
    """End-to-end on the real book under the DEFAULT (cozo): SHACL conforms and the
    competency gate completes — the cutover default works on real ledger data."""
    from scripts.validate_shacl import validate_shacl

    monkeypatch.delenv("KG_BACKEND", raising=False)
    layout = WorkspaceLayout(BERMUDA)
    report = validate_shacl(layout)
    assert report.conforms is True, f"bermuda must conform under cozo: {report.violations}"
    findings = run_competency_queries(layout)
    assert "warnings" in findings, "competency run must return the established shape"
