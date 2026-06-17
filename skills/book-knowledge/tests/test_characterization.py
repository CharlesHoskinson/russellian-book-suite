"""Presence test for the characterization golden fixtures (REQ-KG-005, REQ-KG-014).

The eight current RDF/SPARQL competency queries each get a committed golden
result-set under ``tests/golden/kg/``. These goldens are the equivalence oracle
for the later EDN -> Cozo port: each ported query must reproduce its golden
exactly. This test only asserts the goldens are present; the per-query match is
gated by ``tests/test_query_ports.py`` once the ports land.

The two SHACL goldens (REQ-KG-014) freeze the current pyshacl conformance
behaviour -- ``shacl_report_bermuda`` (the canonical conforming workspace) and
``shacl_report_violating`` (the deliberately-violating C0.1 fixture) -- so the
later SHACL -> EDN -> Cozo port (Phase P2) can be proven equivalent.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.capture_characterization import capture
from scripts.workspace import WorkspaceLayout

GOLDEN = Path(__file__).parent / "golden" / "kg"

# The full set of eight query names (coverage + consistency + defeasible),
# matching the .rq stems under assets/queries/, plus the two SHACL conformance
# goldens (REQ-KG-014).
REQUIRED = [
    "unsupported_claims",
    "chapter_evidence_coverage",
    "orphan_wiki_pages",
    "stale_after_source_refresh",
    "contradiction_scan",
    "contested-rebuttal-window",
    "posterior-floor",
    "rebuttal-presence",
    "shacl_report_bermuda",
    "shacl_report_violating",
]


@pytest.mark.parametrize("name", REQUIRED)
def test_required_goldens_present(name: str) -> None:
    assert (GOLDEN / f"{name}.json").exists(), f"missing golden for {name}"


def test_capture_refuses_empty_dataset(tmp_path: Path) -> None:
    """capture() must abort (and write nothing) when the dataset is empty.

    Pointing the script at a workspace with no projected RDF would otherwise
    write all-empty goldens and commit them as a false equivalence oracle.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    layout = WorkspaceLayout(workspace)
    assert not layout.dataset.exists()  # no graph/dataset.trig

    out_dir = tmp_path / "out"

    with pytest.raises(SystemExit):
        capture(workspace, out_dir)

    # No golden files may have been written.
    written = list(out_dir.glob("*")) if out_dir.exists() else []
    assert written == [], f"capture wrote files despite empty dataset: {written}"


def test_violating_fixture_goldens_nonempty() -> None:
    """The violating SHACL golden must be a non-vacuous failure (REQ-KG-014).

    The C0.1 fixture guarantees exactly 4 violations, so we assert a floor of
    >= 3 (a stronger non-vacuity guard than ">= 1") and that the golden records
    non-conformance. A golden with an empty violation set would be a false
    "everything conforms" oracle for the later SHACL -> EDN -> Cozo port.
    """
    golden = json.loads(
        (GOLDEN / "shacl_report_violating.json").read_text(encoding="utf-8")
    )
    assert golden["conforms"] is False
    violations = golden["violations"]
    assert len(violations) >= 3, f"expected a non-vacuous failure, got {violations}"


def test_bermuda_golden_conforms() -> None:
    """The canonical bermuda-manual workspace golden must record conformance."""
    golden = json.loads(
        (GOLDEN / "shacl_report_bermuda.json").read_text(encoding="utf-8")
    )
    assert golden["conforms"] is True
    assert golden["violations"] == []
