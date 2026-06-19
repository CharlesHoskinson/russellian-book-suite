"""Cites REQ-LIVE-003 (sentence helper for scorers)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.text_util import iter_sentences, Sentence


@pytest.mark.needs_model
def test_iter_sentences_basic():
    sents = iter_sentences("The bank holds your money. You trust it.")
    assert len(sents) == 2
    assert isinstance(sents[0], Sentence)
    assert sents[0].first == "the"
    assert "bank" in sents[0].content and "money" in sents[0].content
    assert "the" not in sents[0].content  # stopword excluded
    assert sents[0].n_alpha >= 4


@pytest.mark.needs_model
def test_score_passage_shape():
    from scripts.score import score_passage
    out = score_passage("The bank holds your money. You trust it.", register="narrative-editorial")
    assert out["register"] == "narrative-editorial"
    assert isinstance(out["signals"], dict)   # empty until scorers register
