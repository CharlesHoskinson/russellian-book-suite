"""Presence test for the characterization golden fixtures (REQ-KG-005).

The eight current RDF/SPARQL competency queries each get a committed golden
result-set under ``tests/golden/kg/``. These goldens are the equivalence oracle
for the later EDN -> Cozo port: each ported query must reproduce its golden
exactly. This test only asserts the goldens are present; the per-query match is
gated by ``tests/test_query_ports.py`` once the ports land.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.capture_characterization import capture
from scripts.workspace import WorkspaceLayout

GOLDEN = Path(__file__).parent / "golden" / "kg"

# The full set of eight query names (coverage + consistency + defeasible),
# matching the .rq stems under assets/queries/.
REQUIRED = [
    "unsupported_claims",
    "chapter_evidence_coverage",
    "orphan_wiki_pages",
    "stale_after_source_refresh",
    "contradiction_scan",
    "contested-rebuttal-window",
    "posterior-floor",
    "rebuttal-presence",
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
