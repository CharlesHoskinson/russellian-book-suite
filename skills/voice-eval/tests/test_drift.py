# skills/voice-eval/tests/test_drift.py
"""Cites REQ-VEVAL-013 (formula-drift: struct TF-IDF cosine + opening POS + analogy reuse)."""
import pytest

pytestmark = pytest.mark.windows_canary


def test_identical_structure_flags_high_drift():
    from scripts.drift import arm_drift
    # Three passages that all open and close with the same structural skeleton.
    skeleton = {"first": ["DET", "NOUN", "VERB"], "last": ["PRON", "VERB", "ADJ"], "opening_pos": ("DET", "NOUN", "VERB")}
    passages = [{"prompt_id": f"P0{i}", "arm": "v2", "text": "t",
                 "structure": skeleton, "analogy_family": "bank"} for i in range(3)]
    out = arm_drift(passages, struct_of=lambda p: p["structure"],
                    analogy_of=lambda p: p["analogy_family"], threshold=0.5)
    assert out["flagged"] is True
    assert out["mean_cosine"] > 0.5
    assert out["analogy_reuse_max"] == 3      # 'bank' reused in all three


def test_varied_structure_below_threshold():
    from scripts.drift import arm_drift
    passages = [
        {"prompt_id": "P01", "arm": "v2", "structure": {"first": ["DET", "NOUN"], "last": ["VERB"], "opening_pos": ("DET", "NOUN")}, "analogy_family": "bank"},
        {"prompt_id": "P02", "arm": "v2", "structure": {"first": ["ADV", "VERB", "PRON"], "last": ["NOUN", "NOUN"], "opening_pos": ("ADV", "VERB")}, "analogy_family": "garden"},
        {"prompt_id": "P03", "arm": "v2", "structure": {"first": ["SCONJ", "PRON", "VERB", "ADJ"], "last": ["DET", "ADJ", "NOUN"], "opening_pos": ("SCONJ", "PRON")}, "analogy_family": "river"},
    ]
    out = arm_drift(passages, struct_of=lambda p: p["structure"],
                    analogy_of=lambda p: p["analogy_family"], threshold=0.7)
    assert out["flagged"] is False
    assert out["analogy_reuse_max"] == 1
