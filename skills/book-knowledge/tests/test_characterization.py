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
