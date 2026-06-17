import dataclasses

import pytest

pytestmark = pytest.mark.windows_canary

from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.validate_shacl import validate_shacl


def test_conforming_workspace_validates(tmp_path):
    """A clean, conforming workspace reports conformance through the (sole) Cozo
    validator, and the report is a ``ShaclReport`` with the public fields callers
    rely on (``conforms`` / ``violations`` / ``text``)."""
    from scripts.ledger import append_claim
    from scripts.validate_shacl import ShaclReport

    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, {
        "claim_id": "clm-2026-000001",
        "canonical_text": "A well-formed base claim.",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.8,
        "source_spans": [{"doc_id": "base-doc", "locator_text": "supporting passage"}],
        "created_at": "2026-01-01T00:00:00+00:00",
    })
    report = validate_shacl(layout)
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
