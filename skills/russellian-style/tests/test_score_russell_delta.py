"""Cites REQ-DELTA-003, REQ-DELTA-004, REQ-DELTA-005, REQ-DELTA-006."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.build_delta_profile import build_profile
from scripts.score_russell_delta import score


@pytest.fixture
def fixture_profile():
    texts = {
        "a": " ".join(["the of and to the of a in the of"] * 400),
        "b": " ".join(["the to and of a the in of the and"] * 400),
    }
    return build_profile(texts, n_features=6, segment_words=50, min_segment=20)

def test_score_shape(fixture_profile):
    r = score("the of and to the of a in the of " * 200, fixture_profile, min_words=1000)
    assert r["metric"] == "russell-cosine-delta"
    assert set(r["band"]) == {"p10", "p50", "p90"}
    assert r["verdict"] in ("within Russell's range", "outside Russell's range")
    assert isinstance(r["delta"], float)

def test_in_distribution_text_is_within_range(fixture_profile):
    r = score("the of and to the of a in the of " * 300, fixture_profile, min_words=10)
    assert r["delta"] <= fixture_profile["internal_delta"]["p90"] + 1e-9
    assert r["verdict"] == "within Russell's range"

def test_out_of_distribution_text_scores_outside(fixture_profile):
    r = score("zebra zebra quux quux blorp blorp " * 300, fixture_profile, min_words=10)
    # Alien words all absent from mfw; z-vector is (-mean/stdev) or zero-guarded,
    # giving cosine_delta >= 1.0 against the reference segments.
    assert r["delta"] >= 1.0

def test_min_length_guard_sets_reliable_false(fixture_profile):
    r = score("the of and the", fixture_profile, min_words=1000)
    assert r["reliable"] is False
    assert r["n_words"] == 4

def test_determinism(fixture_profile):
    t = "the of and to the of a the in of " * 200
    assert score(t, fixture_profile) == score(t, fixture_profile)
