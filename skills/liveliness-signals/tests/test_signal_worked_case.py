"""Cites REQ-LIVE-011 (worked-case presence)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.text_util import iter_sentences
from scripts.signal_worked_case import score


@pytest.mark.needs_model
def test_worked_example_detected():
    out = score(iter_sentences("Trust is abstract. Think about a bank: you never see the vault, yet you rely on it."), "narrative-editorial", None)
    assert out["score"] == 1.0
    assert out["findings"]


@pytest.mark.needs_model
def test_bare_definition_has_no_worked_case():
    out = score(iter_sentences("A nullifier is a unique tag. It prevents double spends."), "technical-exposition", None)
    assert out["score"] == 0.0
