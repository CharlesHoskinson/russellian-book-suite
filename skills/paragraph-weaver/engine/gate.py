# engine/gate.py
"""Acceptance gate: a pure function of FROZEN artifacts.

Non-determinism lives only in artifact *production* (agent stages). score_gate
re-scores the same artifact dict identically, so a PASS is reproducible. v1 gates
on mechanical, deterministic checks only; coherence and goal-attainment are
agent-judged and recorded in the report, not gated numerically (no calibrated
threshold ships in v1).
"""
from __future__ import annotations

from targets.base import GateResult

DEFAULT_BRIDGE_LOAD_CAP = 0.35


def no_silent_drops(input_ids: list[str], output_ids: list[str]) -> tuple[bool, list[str]]:
    missing = sorted(set(input_ids) - set(output_ids))
    extra = sorted(set(output_ids) - set(input_ids))
    reasons: list[str] = []
    if missing:
        reasons.append(f"dropped paragraphs not in output: {missing}")
    if extra:
        reasons.append(f"output contains unexpected ids: {extra}")
    return (not reasons, reasons)


def bridge_load_ratio(source_chars: int, bridge_chars: int) -> float:
    total = source_chars + bridge_chars
    return 0.0 if total == 0 else bridge_chars / total


def score_gate(artifacts: dict) -> GateResult:
    mechanical: dict = {}
    notes: list[str] = []

    ok_drops, drop_reasons = no_silent_drops(artifacts["input_ids"], artifacts["output_ids"])
    mechanical["no_silent_drops"] = ok_drops
    notes.extend(drop_reasons)

    cap = artifacts.get("bridge_load_cap", DEFAULT_BRIDGE_LOAD_CAP)
    ratio = bridge_load_ratio(artifacts.get("source_chars", 0), artifacts.get("bridge_chars", 0))
    mechanical["bridge_load_ratio"] = ratio
    mechanical["bridge_load_ok"] = ratio <= cap
    if ratio > cap:
        notes.append(f"bridge-load {ratio:.2f} exceeds cap {cap:.2f}")

    validity = artifacts.get("bridge_validity", [])
    mechanical["bridges_grounded"] = all(validity)
    if not all(validity):
        notes.append("one or more bridges failed the entity-subset / relation guard")

    passed = ok_drops and mechanical["bridge_load_ok"] and mechanical["bridges_grounded"]
    return GateResult(passed=passed, mechanical=mechanical, notes=notes)
