import dataclasses
import os

import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.validate_shacl import validate_shacl


def test_well_formed_graph_conforms(tmp_path, monkeypatch):
    monkeypatch.setenv("KG_BACKEND", "rdflib")  # pin the legacy pyshacl path (deleted in P5.4)
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.dataset.write_text("", encoding="utf-8")
    report = validate_shacl(layout)
    assert report.conforms is True


def test_unsupported_verified_claim_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("KG_BACKEND", "rdflib")  # pin the legacy pyshacl path (deleted in P5.4)
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    bad_trig = Path("tests/fixtures/ontology_violations/unsupported_verified.trig").read_text(encoding="utf-8")
    layout.dataset.write_text(bad_trig, encoding="utf-8")
    shipped = Path("assets/shapes.ttl").read_text(encoding="utf-8")
    layout.shapes.write_text(shipped, encoding="utf-8")
    report = validate_shacl(layout)
    assert report.conforms is False
    assert any("Verified claims must derive" in v.message for v in report.violations)


def test_cozo_path_matches_contract(tmp_path):
    """KG_BACKEND=cozo routes through the Cozo validator and honours the contract.

    A clean, conforming workspace must report conformance through the Cozo path,
    and the returned object must still be a ``ShaclReport`` with the public
    fields callers rely on (``conforms`` / ``violations`` / ``text``).
    """
    from scripts.ledger import append_claim
    from scripts.project_graph import project_graph
    from scripts.validate_shacl import ShaclReport

    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, {
        "claim_id": "clm-2026-000001",
        "canonical_text": "A well-formed base claim.",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.8,
        "source_spans": [
            {"doc_id": "base-doc", "locator_text": "supporting passage"}
        ],
        "created_at": "2026-01-01T00:00:00+00:00",
    })
    project_graph(layout)

    prior = os.environ.get("KG_BACKEND")
    os.environ["KG_BACKEND"] = "cozo"
    try:
        report = validate_shacl(layout)
    finally:
        if prior is None:
            os.environ.pop("KG_BACKEND", None)
        else:
            os.environ["KG_BACKEND"] = prior

    assert isinstance(report, ShaclReport)
    assert report.conforms is True
    assert report.violations == []
    assert isinstance(report.text, str)


def test_callers_import_unchanged():
    """The public contract callers import (book-compose preflight) is preserved."""
    from scripts.validate_shacl import ShaclReport, Violation, validate_shacl

    assert callable(validate_shacl)
    fields = {f.name for f in dataclasses.fields(ShaclReport)}
    assert {"conforms", "violations", "text"} <= fields
    vfields = {f.name for f in dataclasses.fields(Violation)}
    assert {"focus_node", "path", "message"} <= vfields
