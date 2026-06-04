"""Healer dispatch tests.

Regression for `healer-skips-critical-reasoning-defects`: the bounded
per-ticket Healer only prepares payloads for `hard_fail_tickets`. Critical
D9-D13 reasoning/verification defects must therefore reach the hard-fail set
in the sentinel roll-up so the Healer actually receives them. This exercises
sentinel.aggregate -> write_report -> healer.prepare_payloads end to end.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.healer import prepare_payloads
from scripts.sentinel import aggregate, write_report


def _stage_defects(workspace: Path, defects: list[dict]) -> None:
    qa = workspace / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "defects.json").write_text(json.dumps({"defects": defects}),
                                     encoding="utf-8")


def test_healer_receives_critical_reasoning_defects(tmp_path: Path):
    _stage_defects(tmp_path, [
        {"class": "D9",  "severity": "critical", "where": "ch-01", "detail": "orphan paragraph"},
        {"class": "D10", "severity": "critical", "where": "datalog", "detail": "transitive contradiction"},
        {"class": "D11", "severity": "critical", "where": "ch-02", "detail": "failed entailment"},
        {"class": "D13", "severity": "critical", "where": "doc", "detail": "verification unsat"},
    ])
    report = aggregate(tmp_path)
    write_report(tmp_path, report)

    payloads = prepare_payloads(tmp_path)
    prepared = {p.class_ for p in payloads}
    assert {"D9", "D10", "D11", "D13"} <= prepared, prepared


def test_healer_skips_important_d12(tmp_path: Path):
    # D12 is important (not critical) and must stay soft-gate, so the Healer
    # must not prepare a payload for it.
    _stage_defects(tmp_path, [
        {"class": "D12", "severity": "important", "where": "thesis:x", "detail": "unadvanced"},
    ])
    report = aggregate(tmp_path)
    write_report(tmp_path, report)

    payloads = prepare_payloads(tmp_path)
    assert all(p.class_ != "D12" for p in payloads)
