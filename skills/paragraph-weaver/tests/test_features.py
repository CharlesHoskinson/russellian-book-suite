# tests/test_features.py
from __future__ import annotations

from scripts.features import extract_entities


def test_extracts_content_words_lowercased_sorted():
    ents = extract_entities("Snails carry a calcareous Shell.")
    assert ents == ("calcareous", "carry", "shell", "snails")


def test_filters_short_words_and_stopwords():
    ents = extract_entities("The shell is on the foot.")
    # "the", "is", "on" dropped (stopword/short); "shell", "foot" kept.
    assert ents == ("foot", "shell")


def test_filters_discourse_connectives():
    # Connectives must not register as entities, else they poison bridge checks.
    ents = extract_entities("Therefore however moreover the spiral.")
    assert ents == ("spiral",)


def test_is_deterministic():
    text = "A spiral shell grows by a logarithmic rule."
    assert extract_entities(text) == extract_entities(text)
