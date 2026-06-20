"""Cites REQ-LIVE-009 (analogy = mapped concrete frame, not keyword)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.signal_analogy import score_text


@pytest.mark.needs_model
def test_mapped_concrete_frame_is_analogy():
    # a bank frame recurs and is mapped to the abstract target
    text = ("Trust is abstract. Think of a bank: the bank holds your money in a vault. "
            "The bank hides the vault, yet you rely on the bank as if it were proof.")
    out = score_text(text)
    assert out["score"] == 1.0
    assert out["findings"]


@pytest.mark.needs_model
def test_abstract_prose_without_frame_is_not_analogy():
    out = score_text("Justice and freedom require principled consideration and careful judgement.")
    assert out["score"] == 0.0
