"""Cites REQ-READING-006, REQ-READING-008."""
import json
import pytest
from pathlib import Path
from scripts.reading_scores import flesch_reading_ease, burstiness


def test_flesch_easy_text_scores_high():
    assert flesch_reading_ease("The cat sat on the mat.") > 90

def test_flesch_harder_text_scores_lower_than_easy():
    easy = flesch_reading_ease("The cat sat on the mat. The dog ran.")
    hard = flesch_reading_ease("Consequently, the epistemological ramifications necessitate considerable reconsideration.")
    assert hard < easy

def test_flesch_empty_is_zero():
    assert flesch_reading_ease("") == 0.0

def test_burstiness_uniform_is_low():
    assert burstiness("aa bb cc. dd ee ff. gg hh ii.") == 0.0

def test_burstiness_varied_is_high():
    assert burstiness("Short. " + "word " * 30 + ". Tiny.") > 0.4

def test_burstiness_single_sentence_is_zero():
    assert burstiness("just one sentence here") == 0.0
