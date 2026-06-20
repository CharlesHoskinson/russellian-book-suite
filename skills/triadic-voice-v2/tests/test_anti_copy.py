"""Cites REQ-TRIAD-006 (anti-copy n-gram + taboo alarm)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.anti_copy import check, word_ngrams


def test_verbatim_run_trips_alarm():
    corpus = ["you have to learn how to walk before you can run in this space"]
    draft = "Remember, you have to learn how to walk before you can run, always."
    out = check(draft, corpus)
    assert out["alarm"] is True
    assert out["shared_ngrams"]


def test_original_prose_is_clean():
    corpus = ["a totally unrelated sentence about farming and weather patterns here"]
    draft = "Zero-knowledge proofs decompose one trust into seven testable bets."
    out = check(draft, corpus, taboo=["send the bit not the dossier"])
    assert out["alarm"] is False
    assert not out["shared_ngrams"] and not out["taboo_hits"]
