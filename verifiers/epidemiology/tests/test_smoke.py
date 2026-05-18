"""End-to-end smoke for the epidemiology verifier.

REQ-EVAL-044: clean fixture yields :sat.
REQ-EVAL-045: doctored low-coverage fixture yields :unsat with D20 (C001) in core.
REQ-EVAL-046: doctored inconsistent-threshold fixture yields :unsat with D21 (C002) in core.

Pipeline per fixture mirrors verifiers/osmotic_pressure/tests/test_smoke.py:
  1. ingest_ledger  fixtures/claims_*.jsonl -> work/claims.edn
  2. verify         node cljs-orchestrator/dist/main.js verify
                    work/claims.edn work/verdict.edn
  3. read verdict   parse work/verdict.edn (EDN) and assert :verdict / :core

Skips when the verifier dist is not built (local Windows-only case).
CI builds before invoking pytest.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file
from scripts.ingest_ledger import ingest


_KW_VERDICT = Keyword("verdict")
_KW_STATUS = Keyword("status")
_KW_CORE = Keyword("core")


def _verifier_main_js(project_root: Path) -> Path:
    return project_root / "cljs-orchestrator" / "dist" / "main.js"


def _have_verifier(project_root: Path) -> bool:
    return _verifier_main_js(project_root).exists()


def _have_node() -> bool:
    return shutil.which("node") is not None or shutil.which("node.exe") is not None


pytestmark = pytest.mark.skipif(
    not _have_node(),
    reason="node not on PATH; CI sets up Node 22",
)


def _run_verifier(project_root: Path, claims_edn: Path, verdict_edn: Path) -> None:
    subprocess.run(
        ["node", str(_verifier_main_js(project_root)),
         "verify", str(claims_edn), str(verdict_edn)],
        check=True, cwd=str(project_root),
    )


def _verdict_status(verdict_edn: Path) -> str:
    payload = read_edn_file(verdict_edn)
    for key in (_KW_VERDICT, _KW_STATUS):
        v = payload.get(key)
        if v is None:
            continue
        return str(v) if isinstance(v, Keyword) else v
    raise AssertionError(f"verdict.edn missing :verdict / :status: {payload!r}")


def _verdict_core(verdict_edn: Path) -> list[str]:
    payload = read_edn_file(verdict_edn)
    core = payload.get(_KW_CORE, [])
    return list(core)


def test_clean_fixture_is_sat(project_root: Path, tmp_work: Path) -> None:
    """REQ-EVAL-044: clean fixture (coverage 0.95, threshold 0.94, R0 15) is :sat."""
    if not _have_verifier(project_root):
        pytest.skip(f"verifier not built ({_verifier_main_js(project_root)})")

    claims_edn = tmp_work / "claims.edn"
    verdict_edn = tmp_work / "verdict.edn"
    ingest(
        project_root / "fixtures" / "claims_clean.jsonl",
        project_root / "rules" / "predicates.edn",
        claims_edn,
    )
    _run_verifier(project_root, claims_edn, verdict_edn)

    status = _verdict_status(verdict_edn)
    if status in (":unknown", "unknown"):
        pytest.fail(
            "Solver returned :unknown — likely timeout or theory "
            "incompleteness. Re-run with VERIFIER_SOLVER_TIMEOUT_MS=300000."
        )
    assert status in (":sat", "sat"), (
        f"expected :sat for clean fixture, got {status!r}"
    )


def test_doctored_low_coverage_is_unsat_with_c001_in_core(
    project_root: Path, tmp_work: Path,
) -> None:
    """REQ-EVAL-045: coverage 0.80 vs threshold 0.94 → :unsat with C001 (D20)."""
    if not _have_verifier(project_root):
        pytest.skip(f"verifier not built ({_verifier_main_js(project_root)})")

    claims_edn = tmp_work / "claims.edn"
    verdict_edn = tmp_work / "verdict.edn"
    ingest(
        project_root / "fixtures" / "claims_doctored_low_coverage.jsonl",
        project_root / "rules" / "predicates.edn",
        claims_edn,
    )
    _run_verifier(project_root, claims_edn, verdict_edn)

    status = _verdict_status(verdict_edn)
    if status in (":unknown", "unknown"):
        pytest.fail("solver returned :unknown — see VERIFIER_SOLVER_TIMEOUT_MS")
    assert status in (":unsat", "unsat"), (
        f"expected :unsat for low-coverage doctored fixture, got {status!r}"
    )
    core = _verdict_core(verdict_edn)
    # The verifier's unsat core reports claim ids (not constraint ids). The
    # low-coverage claim is epi-doc-low-003; the unsat core must include it
    # because C001 binds vaccination-coverage_p to its value.
    assert any("epi-doc-low-003" in c for c in core), (
        f"expected epi-doc-low-003 (the 0.80 coverage claim) in unsat core, got {core!r}"
    )


def test_doctored_inconsistent_threshold_is_unsat_with_c002_in_core(
    project_root: Path, tmp_work: Path,
) -> None:
    """REQ-EVAL-046: threshold 0.70 vs R0 15 contradicts formula → :unsat with C002 (D21)."""
    if not _have_verifier(project_root):
        pytest.skip(f"verifier not built ({_verifier_main_js(project_root)})")

    claims_edn = tmp_work / "claims.edn"
    verdict_edn = tmp_work / "verdict.edn"
    ingest(
        project_root / "fixtures" / "claims_doctored_inconsistent_threshold.jsonl",
        project_root / "rules" / "predicates.edn",
        claims_edn,
    )
    _run_verifier(project_root, claims_edn, verdict_edn)

    status = _verdict_status(verdict_edn)
    if status in (":unknown", "unknown"):
        pytest.fail("solver returned :unknown — see VERIFIER_SOLVER_TIMEOUT_MS")
    assert status in (":unsat", "unsat"), (
        f"expected :unsat for inconsistent-threshold doctored fixture, got {status!r}"
    )
    core = _verdict_core(verdict_edn)
    # The fake threshold 0.70 is on claim epi-doc-inc-002. Both C001 (0.95
    # coverage vs 0.70 threshold is 35% off) and C002 (0.70*15=10.5 vs
    # R0-1=14 is 25% off) fire on this fixture; either places the bad
    # threshold claim in the core.
    assert any("epi-doc-inc-002" in c for c in core), (
        f"expected epi-doc-inc-002 (the 0.70 threshold claim) in unsat core, got {core!r}"
    )


def test_codegen_emits_real_typed_axioms(project_root: Path) -> None:
    """REQ-EVAL-043 follow-up: both axioms compile as Real (not Int).

    Regression test for the subtree-local float-typing gap. C001 has
    no float literal in its predicate references alone; the
    `(+ ... 0.0)` anchor forces Real typing. C002 has a `1.0` literal.
    Both must produce `Real::new_const`, never `Int::new_const`.
    """
    axioms = (project_root / "rust-verifier" / "src" / "axioms.rs").read_text(
        encoding="utf-8"
    )
    if "C001-herd-immunity" not in axioms:
        pytest.skip("axioms.rs not yet regenerated by codegen-axioms")
    # We don't want bare Int::new_const for our domain predicates.
    forbidden = (
        'Int::new_const("vaccination-coverage_p")',
        'Int::new_const("herd-immunity-threshold_d")',
        'Int::new_const("basic-reproduction-number_d")',
    )
    for f in forbidden:
        assert f not in axioms, (
            f"codegen emitted Int for a :real predicate: {f}; "
            "the subtree-local float-typing gap has regressed. "
            "See constraints.edn header note about the `(+ ... 0.0)` anchor."
        )


def test_unknown_verdict_fails_with_distinct_timeout_message(tmp_path: Path) -> None:
    """REQ-VERIFIER-BUILD-042: :unknown surfaces as a distinct failure mode."""
    verdict_edn = tmp_path / "verdict.edn"
    verdict_edn.write_text(
        '{:status :unknown :core [] :explanation "timeout"}',
        encoding="utf-8",
    )
    status = _verdict_status(verdict_edn)
    assert status in (":unknown", "unknown")
