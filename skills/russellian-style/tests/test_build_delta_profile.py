"""Cites REQ-DELTA-001, REQ-DELTA-002, REQ-DELTA-006."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.build_delta_profile import strip_gutenberg, segment_tokens, build_profile


def test_strip_gutenberg_removes_boilerplate():
    raw = "header junk\n*** START OF THE PROJECT ***\nreal body here\n*** END OF THE PROJECT ***\nfooter"
    assert strip_gutenberg(raw).strip() == "real body here"

def test_segment_tokens_drops_short_tail():
    segs = segment_tokens(["w"] * 25, size=10, min_size=10)
    assert [len(s) for s in segs] == [10, 10]   # trailing 5 dropped

def test_build_profile_shapes_and_determinism():
    texts = {
        "a": " ".join(["the of and the of cat"] * 200),
        "b": " ".join(["the and of dog the of"] * 200),
    }
    p = build_profile(texts, n_features=4, segment_words=50, min_segment=20)
    assert p["method"] == "cosine-delta"
    assert p["n_features"] == 4
    assert len(p["mfw"]) == 4
    assert p["mfw"][0] == "the"
    assert len(p["mean"]) == 4 and len(p["stdev"]) == 4
    assert len(p["segments_z"]) == p["n_segments"]
    assert all(len(z) == 4 for z in p["segments_z"])
    assert set(p["internal_delta"]) >= {"p10", "p50", "p90", "max", "mean", "count"}
    assert "no source prose" in p["source_policy"].lower()
    p2 = build_profile(texts, n_features=4, segment_words=50, min_segment=20)
    drop = lambda d: {k: v for k, v in d.items() if k != "built_at"}
    assert drop(p) == drop(p2)

def test_build_profile_needs_two_segments():
    with pytest.raises(ValueError):
        build_profile({"a": "the of and"}, n_features=2, segment_words=50, min_segment=20)
