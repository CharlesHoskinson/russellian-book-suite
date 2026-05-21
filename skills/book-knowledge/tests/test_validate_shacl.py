import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.validate_shacl import validate_shacl


def test_well_formed_graph_conforms(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.dataset.write_text("", encoding="utf-8")
    report = validate_shacl(layout)
    assert report.conforms is True


def test_unsupported_verified_claim_fails(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    bad_trig = Path("tests/fixtures/ontology_violations/unsupported_verified.trig").read_text(encoding="utf-8")
    layout.dataset.write_text(bad_trig, encoding="utf-8")
    shipped = Path("assets/shapes.ttl").read_text(encoding="utf-8")
    layout.shapes.write_text(shipped, encoding="utf-8")
    report = validate_shacl(layout)
    assert report.conforms is False
    assert any("Verified claims must derive" in v.message for v in report.violations)
