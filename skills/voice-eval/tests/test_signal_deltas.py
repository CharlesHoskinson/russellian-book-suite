# skills/voice-eval/tests/test_signal_deltas.py
"""Cites REQ-VEVAL-011 (per-signal mean deltas, overall + per register)."""
import pytest

pytestmark = pytest.mark.windows_canary

SIGNALS = ("cadence", "verb_energy")


def _scorer(table):
    # table[(prompt_id, arm)] -> {signal: value}
    def score(text, register, prompt_id, arm):
        return {s: {"score": table[(prompt_id, arm)][s]} for s in SIGNALS}
    return score


def test_overall_and_per_register_deltas():
    from scripts.signal_deltas import compute_deltas
    passages = [
        {"prompt_id": "T01", "arm": "v1", "register": "technical-exposition", "text": "a"},
        {"prompt_id": "T01", "arm": "v2", "register": "technical-exposition", "text": "b"},
        {"prompt_id": "P01", "arm": "v1", "register": "polemic", "text": "c"},
        {"prompt_id": "P01", "arm": "v2", "register": "polemic", "text": "d"},
    ]
    table = {
        ("T01", "v1"): {"cadence": 0.4, "verb_energy": 0.2},
        ("T01", "v2"): {"cadence": 0.6, "verb_energy": 0.5},
        ("P01", "v1"): {"cadence": 0.5, "verb_energy": 0.1},
        ("P01", "v2"): {"cadence": 0.5, "verb_energy": 0.4},
    }
    out = compute_deltas(passages, scorer=_scorer(table), signals=SIGNALS)
    # cadence overall delta = mean(0.2, 0.0) = 0.1 ; verb_energy = mean(0.3, 0.3) = 0.3
    assert round(out["overall"]["cadence"], 6) == 0.1
    assert round(out["overall"]["verb_energy"], 6) == 0.3
    assert round(out["per_register"]["technical-exposition"]["cadence"], 6) == 0.2
    assert round(out["per_register"]["polemic"]["cadence"], 6) == 0.0
