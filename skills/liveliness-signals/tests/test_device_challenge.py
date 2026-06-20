"""Cites REQ-LIVE-013 (device-challenge set: the sample is not 'absent')."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.score import score_passage

SAMPLE = ("Here's why that matters. Think about what you do when a bank tells you your balance is correct. "
          "You trust the bank: one trust, one black box. What people miss is that every part is independently testable.")


@pytest.mark.needs_model
def test_sample_registers_curiosity_and_worked_case():
    out = score_passage(SAMPLE, register="narrative-editorial")
    assert out["signals"]["curiosity"]["score"] > 0.0      # not curiosity-absent
    assert out["signals"]["worked_case"]["score"] == 1.0   # bank worked example present


@pytest.mark.needs_model
def test_sample_is_verb_driven_and_tightly_bound():
    out = score_passage(SAMPLE, register="narrative-editorial")
    assert out["signals"]["verb_energy"]["score"] > 0.12   # action-bearing prose
    assert out["signals"]["sv_distance"]["score"] >= 0.93  # mostly tight subject-verb


@pytest.mark.needs_model
def test_sample_registers_concrete_anchor_and_analogy():
    out = score_passage(SAMPLE, register="narrative-editorial")
    assert out["signals"]["concrete_anchor"]["score"] > 0.0   # bank / box / wall are concrete
    assert out["signals"]["analogy_mapping"]["score"] == 1.0   # bank frame mapped -> not analogy-absent
