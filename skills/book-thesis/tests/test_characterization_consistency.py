"""Characterization goldens for the Datalog D9/D10/D11 consistency pass.

Two committed goldens under ``tests/golden/consistency/`` freeze the current
pyDatalog behaviour so the later pyDatalog -> EDN -> Cozo port (Phase P3) can be
proven equivalent (REQ-KG-014):

* ``d9_d11_bermuda.json`` — the canonical ``examples/bermuda-manual`` baseline
  (may legitimately have zero defects: a clean book).
* ``d9_d11_violating.json`` — captured from :func:`build_violating_thesis`,
  which guarantees a non-vacuous failure: >=1 defect of each class D9, D10, D11
  (with >=1 ``invariant_violation``).

This file asserts the goldens are present and that the violating golden is
non-vacuous; the byte-for-byte port equivalence is gated later in Phase P3.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.windows_canary

GOLDEN = Path(__file__).parent / "golden" / "consistency"

REQUIRED = ["d9_d11_bermuda", "d9_d11_violating"]


@pytest.mark.parametrize("name", REQUIRED)
def test_required_consistency_goldens_present(name: str) -> None:
    assert (GOLDEN / f"{name}.json").exists(), f"missing consistency golden for {name}"


def test_bermuda_consistency_golden_is_clean() -> None:
    """The bermuda golden is the clean baseline: it must have zero defects. The
    Phase-P3 equivalence oracle depends on this clean baseline, so guard it
    against silent drift."""
    golden = json.loads((GOLDEN / "d9_d11_bermuda.json").read_text(encoding="utf-8"))
    defects = golden["defects"]
    assert defects == [], f"bermuda baseline golden is not clean: {defects}"


def test_violating_consistency_golden_nonvacuous() -> None:
    """The violating golden must contain >=1 D9, >=1 D10, AND >=1 D11 defect,
    with >=1 of class D11 being an ``invariant_violation`` (REQ-KG-014). An
    empty or single-class golden would be a false "mostly clean" oracle for the
    later pyDatalog -> EDN -> Cozo port."""
    golden = json.loads((GOLDEN / "d9_d11_violating.json").read_text(encoding="utf-8"))
    defects = golden["defects"]
    classes = {d["class"] for d in defects}
    assert "D9" in classes, f"no D9 orphan in violating golden: {defects}"
    assert "D10" in classes, f"no D10 contradiction in violating golden: {defects}"
    assert "D11" in classes, f"no D11 invariant in violating golden: {defects}"
    rules = {d["rule"] for d in defects}
    assert "invariant_violation" in rules, (
        f"no invariant_violation in violating golden: {defects}"
    )
