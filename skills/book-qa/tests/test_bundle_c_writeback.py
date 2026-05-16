"""End-to-end test for the Bundle C closed-loop writeback chain.

Until this fix the chain was broken: ``lint_artifact`` emitted
``qa/defects.json`` with no ``claim_id`` field, and ``propose_writeback``
read fixture-only files (``lint-findings.json`` / ``swarm-findings.json``)
that production never produced. This test wires a real workspace:

  1. seed ``claims/ledger.jsonl`` with one verified claim,
  2. seed ``qa/entailment-results.json`` so D11 (failed entailment) emits
     a defect whose ``where`` carries the claim_id,
  3. run ``lint_artifact.main`` to produce ``qa/defects.json``,
  4. run ``propose_writeback`` and assert the proposed-transitions.jsonl
     contains the expected ``verified -> disputed`` transition.

The test exercises the round-trip that real builds will follow.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.lint_artifact import main as lint_main
from scripts.propose_writeback import propose_writeback


MANUSCRIPT_MD = """\
# Chapter 1: Bundle C

## Table of Contents

1. Bundle C

---

Russell argued that propositions decompose into atomic constituents.
The argument advances by entailment, not by citation, and the prose
should support the supported claim without falling back on identifiers.

This second paragraph holds the line at ordinary readable length so
the linter has something to measure beyond a single sentence.
"""


def _seed_ledger(workspace: Path, claim_id: str, status: str) -> None:
    """Write a one-record claim ledger; minimal schema sufficient for status lookup."""
    (workspace / "claims").mkdir(parents=True, exist_ok=True)
    record = {
        "claim_id": claim_id,
        "canonical_text": "Stand-in canonical text for the bundle-C round-trip test.",
        "status": status,
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "test", "locator_text": "test span"}],
        "created_at": "2026-05-16T00:00:00+00:00",
    }
    (workspace / "claims" / "ledger.jsonl").write_text(
        json.dumps(record, sort_keys=True) + "\n", encoding="utf-8"
    )


def _seed_release(workspace: Path, version: str) -> None:
    """Drop a minimal manuscript into book/releases/<version>/."""
    release = workspace / "book" / "releases" / version
    release.mkdir(parents=True, exist_ok=True)
    (release / "manuscript.md").write_text(MANUSCRIPT_MD, encoding="utf-8")


def _seed_entailment_with_claim_id(workspace: Path, claim_id: str) -> None:
    """Seed a D11 side-file whose ``where`` carries the claim id so the
    Defect enrichment step recovers it via the clm regex."""
    qa = workspace / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    payload = {
        "results": [
            {
                # The linter trusts `where` (or paragraph_id) for the location
                # field; putting the claim_id here lets _enrich_defects bind it.
                "where": claim_id,
                "paragraph_id": "ch-01-p2",
                "supports": "atomic-decomposition",
                "verdict": "contradicts",
                "detail": (
                    f"paragraph ch-01-p2 contradicts supports=atomic-decomposition "
                    f"(claim {claim_id})"
                ),
            }
        ]
    }
    (qa / "entailment-results.json").write_text(json.dumps(payload), encoding="utf-8")


def test_bundle_c_closed_loop_verified_to_disputed(tmp_path: Path) -> None:
    """Round-trip from a verified claim through lint+writeback to a disputed transition.

    Wires the full closed loop:

      ledger.jsonl  -->  lint_artifact.main  -->  defects.json  -->
        propose_writeback  -->  proposed-transitions.jsonl

    Asserts the proposed transition is verified -> disputed for the
    bound claim_id, which is exactly the production behaviour Bundle C
    was supposed to deliver.
    """
    workspace = tmp_path
    claim_id = "clm-2026-000042"
    version = "v0.bundle-c"

    _seed_release(workspace, version)
    _seed_ledger(workspace, claim_id, status="verified")
    _seed_entailment_with_claim_id(workspace, claim_id)

    # Run lint_artifact end-to-end via its CLI entry point. Exit code may be
    # nonzero (we deliberately seeded a critical D11), so do not assert on it.
    lint_main(["lint_artifact.py", str(workspace), version])

    defects_path = workspace / "qa" / "defects.json"
    assert defects_path.exists(), "lint_artifact must emit qa/defects.json"
    payload = json.loads(defects_path.read_text(encoding="utf-8"))

    bound = [d for d in payload["defects"] if d.get("claim_id") == claim_id]
    assert bound, (
        "expected at least one defect bound to the seeded claim_id; "
        f"got defects: {payload['defects']}"
    )
    assert all("id" in d for d in payload["defects"]), \
        "every emitted defect must carry a stable id field"
    statuses = {d.get("claim_current_status") for d in bound}
    assert statuses == {"verified"}, (
        f"enrichment must read claim_current_status from ledger; got {statuses}"
    )

    propose_writeback(workspace, version=version)
    proposed_path = workspace / "claims" / "proposed-transitions.jsonl"
    assert proposed_path.exists(), "propose_writeback must emit proposed-transitions.jsonl"
    lines = [
        json.loads(line)
        for line in proposed_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matching = [
        p for p in lines
        if p.get("kind") == "claim"
        and p.get("claim_id") == claim_id
        and p.get("from") == "verified"
        and p.get("to") == "disputed"
    ]
    assert matching, (
        f"expected a verified->disputed transition for {claim_id}; got {lines}"
    )
    assert matching[0]["cause_class"] == "unsupported_claim", (
        "D11 must dispatch through the unsupported_claim transition synonym"
    )
