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

def test_build_scoring_prompt_contains_rubric_doc_scale_and_dims():
    from scripts.reading_scores import build_scoring_prompt
    p = build_scoring_prompt("RUBRIC-TEXT-HERE", "DOC-TEXT-HERE")
    assert "RUBRIC-TEXT-HERE" in p and "DOC-TEXT-HERE" in p
    assert "1 to 5" in p
    for dim in ("enjoyment", "flow", "style", "quality"):
        assert dim in p.lower()

def test_aggregate_medians_and_overall():
    from scripts.reading_scores import aggregate_reading_scores
    scores = [
        {"enjoyment": 4, "flow": 3, "style": 4, "quality": 5, "note": "PERSONA-A-SECRET"},
        {"enjoyment": 2, "flow": 3, "style": 4, "quality": 3, "note": "PERSONA-B-SECRET"},
        {"enjoyment": 3, "flow": 4, "style": 2, "quality": 4, "note": "PERSONA-C-SECRET"},
    ]
    rep = aggregate_reading_scores(scores, "The cat sat on the mat. The dog ran fast today.")
    assert rep["enjoyment"] == 3 and rep["flow"] == 3 and rep["style"] == 4 and rep["quality"] == 4
    assert rep["overall"] == round((3 + 3 + 4 + 4) / 4, 2)
    assert set(rep["deterministic"]) == {"flesch", "burstiness"}
    assert isinstance(rep["verdict"], str) and rep["verdict"]

def test_aggregate_does_not_leak_persona_text():
    from scripts.reading_scores import aggregate_reading_scores
    scores = [{"enjoyment": 4, "flow": 4, "style": 4, "quality": 4, "note": "PERSONA-A-SECRET"}]
    rep = aggregate_reading_scores(scores, "A short document with several plain words in it here.")
    assert "PERSONA-A-SECRET" not in json.dumps(rep)

def test_aggregate_empty_raises():
    from scripts.reading_scores import aggregate_reading_scores
    with pytest.raises(ValueError):
        aggregate_reading_scores([], "text")
