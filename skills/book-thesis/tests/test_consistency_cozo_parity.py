"""P3.2 — the EDN/Cozo D9-D11 consistency pass reproduces the pyDatalog goldens.

REQ-KG-015. ``consistency_cozo.run_consistency_cozo(workspace)`` projects the
thesis spine (P3.1) + claim facts into book-knowledge's Cozo store, runs the
recursive CozoScript consistency program (rules/consistency.cozo), and assembles
the SAME ``DefectReport.as_payload()`` the pyDatalog pass (datalog_consistency.run)
emits — proven equal on the two frozen C0.3 goldens:

* violating: build_violating_thesis -> 6 defects (D9 orphan, D10 direct x2 +
  transitive, D11 invariant_violation + unreachable_supports).
* bermuda: examples/bermuda-manual -> 0 defects (clean baseline).

The Cozo pass also runs as the parity oracle directly against the live pyDatalog
pass, so the equivalence is not merely golden-vs-golden.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.compile_thesis import compile_thesis
from scripts.consistency_cozo import run_consistency_cozo
from scripts.datalog_consistency import run as run_pydatalog

from tests.fixtures.violating_thesis import build_violating_thesis

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "golden" / "consistency"
BERMUDA = ROOT.parents[1] / "examples" / "bermuda-manual"


def _golden(name: str) -> dict:
    return json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))


def test_violating_matches_golden(tmp_path):
    ws = build_violating_thesis(tmp_path)
    assert run_consistency_cozo(ws) == _golden("d9_d11_violating")


def test_violating_matches_live_pydatalog(tmp_path):
    """Non-tautological: the Cozo payload equals the LIVE pyDatalog payload on the
    same workspace, not just the frozen golden."""
    ws = build_violating_thesis(tmp_path)
    assert run_consistency_cozo(ws) == run_pydatalog(ws).as_payload()


@pytest.mark.skipif(not BERMUDA.exists(), reason="bermuda workspace not present")
def test_bermuda_matches_golden_clean_baseline():
    assert run_consistency_cozo(BERMUDA) == _golden("d9_d11_bermuda")


_MISSING_EV_YAML = """\
book_id: missing-ev
thesis:
  statement: A thesis with one unmet evidence slot.
  polarity: descriptive
  scope: test fixture
sub_arguments:
  - id: leg
    parent: thesis
    statement: The sole leg.
    polarity: descriptive
    required_evidence: [geography]
    advanced_by_chapters: [ch-01]
"""


def _build_missing_evidence_workspace(tmp_path) -> Path:
    """A workspace whose only defect is a missing-evidence slot, reached through
    the full project_consistency_facts -> sub_arg_evidence -> missing_evidence
    path. The lone verified claim carries a semantic_class (so have_subjects is
    True, un-gating missing_evidence) but no claim meets the 'geography' slot."""
    ws = Path(tmp_path)
    (ws / "thesis").mkdir(parents=True, exist_ok=True)
    (ws / "thesis" / "missing-ev.yaml").write_text(_MISSING_EV_YAML, encoding="utf-8", newline="\n")
    compile_thesis(ws, "missing-ev")
    (ws / "claims").mkdir(parents=True, exist_ok=True)
    (ws / "claims" / "ledger.jsonl").write_text(
        json.dumps({"claim_id": "clm-x", "status": "verified",
                    "semantic_class": "economics"}, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    return ws


def test_missing_evidence_end_to_end_matches_live(tmp_path):
    """Closes the end-to-end gap for the have_subjects-gated missing_evidence
    branch (rule-level coverage exists in test_consistency_cozo_rules; this drives
    it through run_consistency_cozo and proves equality with the live pyDatalog)."""
    ws = _build_missing_evidence_workspace(tmp_path)
    cozo = run_consistency_cozo(ws)
    assert cozo == run_pydatalog(ws).as_payload()
    assert "missing_evidence" in {d["rule"] for d in cozo["defects"]}
