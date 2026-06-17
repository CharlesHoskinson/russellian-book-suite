"""P3.2 — the EDN/Cozo D9-D11 consistency pass reproduces the pyDatalog goldens.

REQ-KG-015. ``consistency_cozo.run_consistency_cozo(workspace)`` projects the
thesis spine (P3.1) + claim facts into book-knowledge's Cozo store, runs the
recursive CozoScript consistency program (rules/consistency.cozo), and assembles
the same canonically-sorted ``DefectReport.as_payload()`` shape the (now deleted,
P5.4b) pyDatalog pass emitted — frozen into the two C0.3 goldens:

* violating: build_violating_thesis -> 6 defects (D9 orphan, D10 direct x2 +
  transitive, D11 invariant_violation + unreachable_supports).
* bermuda: examples/bermuda-manual -> 0 defects (clean baseline).

Before pyDatalog was removed, the Cozo pass was proven equal to the LIVE pyDatalog
run on these workspaces (not merely golden-vs-golden); the goldens are now the oracle.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.compile_thesis import compile_thesis
from scripts.consistency_cozo import run_consistency_cozo

from tests.fixtures.violating_thesis import build_violating_thesis

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "golden" / "consistency"
BERMUDA = ROOT.parents[1] / "examples" / "bermuda-manual"


def _golden(name: str) -> dict:
    return json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))


def test_violating_matches_golden(tmp_path):
    # The golden was the live pyDatalog output, frozen in C0.3; the Cozo pass was
    # proven equal to the LIVE pyDatalog run before that pass was deleted in P5.4b
    # (see the run log). The frozen golden is now the oracle.
    ws = build_violating_thesis(tmp_path)
    assert run_consistency_cozo(ws) == _golden("d9_d11_violating")


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


def test_missing_evidence_end_to_end(tmp_path):
    """End-to-end coverage of the have_subjects-gated missing_evidence branch through
    run_consistency_cozo (rule-level coverage is in test_consistency_cozo_rules)."""
    ws = _build_missing_evidence_workspace(tmp_path)
    cozo = run_consistency_cozo(ws)
    assert "missing_evidence" in {d["rule"] for d in cozo["defects"]}


_CLEAN_YAML = """\
book_id: clean
thesis:
  statement: A clean thesis with no defects.
  polarity: descriptive
  scope: test fixture
sub_arguments:
  - id: leg
    parent: thesis
    statement: The sole, chapter-advanced leg.
    polarity: descriptive
    advanced_by_chapters: [ch-01]
"""


def _build_clean_workspace(tmp_path) -> Path:
    ws = Path(tmp_path)
    (ws / "thesis").mkdir(parents=True, exist_ok=True)
    (ws / "thesis" / "clean.yaml").write_text(_CLEAN_YAML, encoding="utf-8", newline="\n")
    compile_thesis(ws, "clean")
    return ws


def test_cli_gates_and_writes_artifact_on_defects(tmp_path):
    """The Cozo CLI must preserve the legacy QA-gate contract (audit CRITICAL):
    nonzero exit when defects exist + a qa/datalog-defects.json in the legacy
    shape. datalog_consistency.main returns 1 on gate failure and run() writes the
    artifact."""
    import scripts.consistency_cozo as cc

    ws = build_violating_thesis(tmp_path)
    rc = cc.main(["consistency_cozo.py", str(ws)])
    assert rc == 1, "violating workspace must fail the gate (nonzero exit)"
    artifact = ws / "qa" / "datalog-defects.json"
    assert artifact.exists(), "CLI must write qa/datalog-defects.json"
    assert json.loads(artifact.read_text(encoding="utf-8")) == _golden("d9_d11_violating")


def test_cli_returns_zero_on_clean(tmp_path):
    import scripts.consistency_cozo as cc

    ws = _build_clean_workspace(tmp_path)
    rc = cc.main(["consistency_cozo.py", str(ws)])
    assert rc == 0
    assert run_consistency_cozo(ws)["summary"] == {
        "contradictions": 0, "orphans": 0, "invariant_violations": 0,
    }


def test_run_consistency_cozo_is_pure_without_write_flag(tmp_path):
    """The library function must NOT write the artifact unless asked (so a parity
    call against a real workspace, e.g. bermuda, has no side effects)."""
    ws = _build_clean_workspace(tmp_path)
    run_consistency_cozo(ws)
    assert not (ws / "qa" / "datalog-defects.json").exists()

