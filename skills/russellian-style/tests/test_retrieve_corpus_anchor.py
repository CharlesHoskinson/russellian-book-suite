"""retrieve_corpus_anchor: same-mode Russell paragraph retrieval."""
import pytest


def test_retrieve_anchor_returns_exemplar_for_known_source_id():
    from scripts.retrieve_corpus_anchor import retrieve_anchor
    ref = retrieve_anchor(rhetorical_mode="problems", seed=42)
    assert ref.corpus_id.startswith("problems-")
    assert ref.source_title
    assert ref.source_url.startswith("https://")
    assert ref.rhetorical_move


def test_retrieve_anchor_accepts_mode_tag():
    """`popular_philosophy` is a mode tag on the `problems` source; should match."""
    from scripts.retrieve_corpus_anchor import retrieve_anchor
    ref = retrieve_anchor(rhetorical_mode="popular_philosophy", seed=42)
    assert ref.corpus_id.startswith("problems-")


def test_retrieve_anchor_seed_stable():
    from scripts.retrieve_corpus_anchor import retrieve_anchor
    a = retrieve_anchor(rhetorical_mode="problems", seed=42)
    b = retrieve_anchor(rhetorical_mode="problems", seed=42)
    assert a == b


def test_retrieve_anchor_filters_by_move_substring():
    from scripts.retrieve_corpus_anchor import retrieve_anchor
    ref = retrieve_anchor(rhetorical_mode="political-ideals", rhetorical_move="liberty", seed=42)
    needle = "liberty"
    assert (
        needle in ref.rhetorical_move.lower()
        or needle in ref.calibration_lesson.lower()
    )


def test_retrieve_anchor_unknown_mode_raises():
    from scripts.retrieve_corpus_anchor import retrieve_anchor
    with pytest.raises(ValueError):
        retrieve_anchor(rhetorical_mode="nonexistent-mode", seed=42)


def test_retrieve_anchor_no_move_match_raises():
    from scripts.retrieve_corpus_anchor import retrieve_anchor
    with pytest.raises(LookupError):
        retrieve_anchor(rhetorical_mode="problems", rhetorical_move="aardvark-zebra", seed=42)
