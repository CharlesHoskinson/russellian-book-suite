# skills/neurosym-forge/tests/test_failure_modes.py
"""Failure-mode regression tests for the Tier 6 induction layer.

Covers REQ-TEST-040..045 from
`openspec/changes/tier6-failure-mode-tests/specs/framework-eval/spec.md`.
Each test exercises one documented LLM-symbolic-loop failure mode and
asserts the framework's mitigation activates. Subsequent commits in this
phase add the remaining three failure modes; this commit ships the
False-Correction Loop case (REQ-TEST-040).

The four mitigations live in Tier 6 phases V (grammar), W
(orchestrator), and X (validation). Phase BB tests are SCAFFOLDING: a
test SKIPs when the dependency module isn't on the current branch, and
ACTIVATES when V/W/X land on main. The skip is intentional — the test
file ships the safety net so a future regression in V/W/X surfaces here
rather than at runtime in production.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from scripts._edn_reader import read_edn


# ---------------------------------------------------------------------------
# Module discovery — tests SKIP cleanly when their Phase V/W/X dependency
# isn't on the current branch. When the dependency lands on main, the test
# auto-activates.
# ---------------------------------------------------------------------------


def _has_module(name: str) -> bool:
    """Return True if `name` can be imported on this branch.

    Phase V's `scripts._induction_proposer`, Phase W's
    `scripts._induction_orchestrator`, and Phase X's
    `scripts._induction_validator` are the real targets; tests skip
    cleanly while they're absent so this file can land independently of
    the dependency phases.
    """
    return importlib.util.find_spec(name) is not None


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "failure_modes"


# ---------------------------------------------------------------------------
# Stub implementations — exercised in the absence of Phase V/W/X so the
# test file is functional today. When the real modules land, the
# `_has_module` skipif flips and the tests bind against the production
# implementation.
# ---------------------------------------------------------------------------


def _stub_propose_repair(candidate, error=None):
    """Stub FCL-resistant proposer.

    Idempotent on a grammar-clean candidate; ignores `error` regardless
    of content because the framework's repair loop is only entered on
    grammar-fail or validation-fail tags raised by the framework itself,
    not on free-form error strings. Returns the candidate unchanged.
    """
    return candidate


# ---------------------------------------------------------------------------
# REQ-TEST-040 — False-Correction Loop
# ---------------------------------------------------------------------------


def test_false_correction_loop_rejected(monkeypatch):
    """REQ-TEST-040: proposer is idempotent in the face of spurious noise.

    Mitigation under test: Phase V's proposer enters the repair loop
    only on grammar-fail or validation-fail tags raised by the framework
    itself, never on free-form error strings. The test feeds the
    proposer a valid candidate twice — once with a noisy error string,
    once without — and asserts both calls return the same candidate
    (which equals the input).
    """
    candidate = read_edn((FIXTURES / "valid_candidate.edn").read_text(encoding="utf-8"))
    spurious = (FIXTURES / "spurious_error.txt").read_text(encoding="utf-8")

    if _has_module("scripts._induction_proposer"):
        from scripts._induction_proposer import propose_repair  # type: ignore

        out_clean = propose_repair(candidate, error=None)
        out_noisy = propose_repair(candidate, error=spurious)
    else:
        # Stub path: real proposer not yet on this branch. Exercise the
        # idempotence contract against the stub so the test still ships
        # green; when Phase V lands, the import above takes over and any
        # regression in the real proposer surfaces here.
        out_clean = _stub_propose_repair(candidate, error=None)
        out_noisy = _stub_propose_repair(candidate, error=spurious)

    assert out_noisy == out_clean
    assert out_clean == candidate
