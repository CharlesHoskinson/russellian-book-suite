"""Pure governance filter: rule-id → pass | quarantine | unknown.

Wired into `forge induce --governance-gate` (Task 14) to drop rules
failing the schools-of-thought policy before they reach the prov sidecar.
"""
from __future__ import annotations
from collections import defaultdict
from enum import Enum
from ._positions_io import Position
from ._stance import Stance


class GateDecision(str, Enum):
    PASS = "pass"
    QUARANTINE_INSUFFICIENT_SUPPORT = "quarantine-insufficient-support"
    QUARANTINE_CONTRADICTED = "quarantine-contradicted"
    UNKNOWN = "unknown"  # rule not in positions ledger


def governance_filter(
    rule_ids: list[str],
    positions: list[Position],
    min_supports: int = 2,
    max_contradictors: int = 0,
) -> dict[str, GateDecision]:
    by_rule: dict[str, list[Position]] = defaultdict(list)
    for p in positions:
        by_rule[p.rule_id].append(p)

    out: dict[str, GateDecision] = {}
    for rule_id in rule_ids:
        rows = by_rule.get(rule_id, [])
        if not rows:
            out[rule_id] = GateDecision.UNKNOWN
            continue
        n_sup = sum(1 for r in rows if r.stance == Stance.SUPPORTS)
        n_con = sum(1 for r in rows if r.stance == Stance.CONTRADICTS)
        if n_con > max_contradictors:
            out[rule_id] = GateDecision.QUARANTINE_CONTRADICTED
        elif n_sup < min_supports:
            out[rule_id] = GateDecision.QUARANTINE_INSUFFICIENT_SUPPORT
        else:
            out[rule_id] = GateDecision.PASS
    return out
