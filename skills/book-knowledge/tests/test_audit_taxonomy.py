import pytest

pytestmark = pytest.mark.windows_canary

from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.audit_taxonomy import audit_taxonomy

ROLE_SUBCLASS_OF_PERSON = """
@prefix tbf: <https://example.org/book-knowledge#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
tbf:Editor rdfs:subClassOf tbf:Person .
"""


def test_flags_role_as_subclass_of_identity_class(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.dataset.write_text(ROLE_SUBCLASS_OF_PERSON, encoding="utf-8")
    findings = audit_taxonomy(layout)
    assert findings, "expected at least one warning"
    assert any("Role" in f["message"] or "role" in f["message"].lower() for f in findings)


def test_clean_taxonomy_yields_no_findings(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.dataset.write_text("", encoding="utf-8")
    assert audit_taxonomy(layout) == []
