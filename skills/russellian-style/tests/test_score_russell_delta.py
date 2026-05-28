"""Cites REQ-DELTA-003, REQ-DELTA-004, REQ-DELTA-005, REQ-DELTA-006."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.build_delta_profile import build_profile
from scripts.score_russell_delta import score, _verdict


def _spacy_model_available():
    try:
        import spacy
        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False


@pytest.fixture
def fixture_profile():
    texts = {
        "a": " ".join(["the of and to the of a in the of"] * 400),
        "b": " ".join(["the to and of a the in of the and"] * 400),
    }
    return build_profile(texts, n_features=6, segment_words=50, min_segment=20)


# A hand-built profile lets the verdict tests control the band directly.
# (build_profile fixtures from uniform repeats collapse stdev to ~0.)
STUB = {
    "mfw": ["the", "of", "and"],
    "mean": [0.5, 0.3, 0.2],
    "stdev": [0.05, 0.05, 0.05],
    "centroid_delta": {"p10": 0.4, "p50": 0.7, "p90": 1.0},
}


def test_score_shape(fixture_profile):
    r = score("the of and to the of a in the of " * 200, fixture_profile, min_words=1000)
    assert r["metric"] == "russell-burrows-delta"
    assert set(r["band"]) == {"p10", "p50", "p90"}
    assert r["verdict"] in ("within Russell's range",
                            "at the edge of Russell's range",
                            "outside Russell's range")
    assert isinstance(r["delta"], float)

def test_verdict_three_bands():
    band = {"p10": 0.6, "p50": 0.7, "p90": 0.8}   # fence = 0.8 + (0.8-0.6) = 1.0
    assert _verdict(0.70, band) == "within Russell's range"
    assert _verdict(0.90, band) == "at the edge of Russell's range"
    assert _verdict(1.20, band) == "outside Russell's range"

def test_within_verdict_when_near_profile():
    # freqs the=0.5, of=0.3, and=0.2 exactly match the profile mean -> delta 0 -> within
    r = score("the the the the the of of of and and", STUB, min_words=1)
    assert r["delta"] == pytest.approx(0.0)
    assert r["verdict"] == "within Russell's range"

def test_outside_verdict_when_far_from_profile():
    # all weight on 'and' -> large absolute z across features -> delta above p90 -> outside
    r = score("and and and and and", STUB, min_words=1)
    assert r["delta"] > STUB["centroid_delta"]["p90"]
    assert r["verdict"] == "outside Russell's range"

def test_min_length_guard_sets_reliable_false(fixture_profile):
    r = score("the of and the", fixture_profile, min_words=1000)
    assert r["reliable"] is False
    assert r["n_words"] == 4

def test_determinism(fixture_profile):
    t = "the of and to the of a the in of " * 200
    assert score(t, fixture_profile) == score(t, fixture_profile)


@pytest.mark.skipif(not _spacy_model_available(),
                    reason="spaCy en_core_web_sm model not installed")
def test_report_dict_includes_russell_delta(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    md = tmp_path / "s.md"
    md.write_text("# T\n\n" + ("The nineteenth century discovered pure mathematics. " * 60), encoding="utf-8")
    rep = generate_report_dict(md)
    assert rep["russell_delta"]["metric"] == "russell-burrows-delta"
    assert "verdict" in rep["russell_delta"]
