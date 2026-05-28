"""Offline tests for the poetry-aware segmentation. No network.

The actual scrapling-driven build is run-once by the orchestrator and not exercised
in CI (network-using; the suite's network boundary is scrapling-fetch).
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from build_longfellow_corpus import segment_stanzas, build_index


VERSE = """\
Should you ask me, whence these stories?
Whence these legends and traditions,
With the odors of the forest,
With the dew and damp of meadows?

Dark behind it rose the forest,
Rose the black and gloomy pine-trees,
Rose the firs with cones upon them;
Bright before it beat the water,
Beat the clear and sunny water,
Beat the shining Big-Sea-Water.

(single line block ignored)
"""


def test_segment_returns_only_multiline_stanzas():
    stanzas = segment_stanzas(VERSE, min_lines=2)
    assert len(stanzas) == 2
    assert stanzas[0].startswith("Should you ask me")
    assert "single line" not in stanzas[1]


def test_segment_preserves_line_breaks():
    stanzas = segment_stanzas(VERSE, min_lines=2)
    assert "\n" in stanzas[0]
    assert stanzas[0].count("\n") == 3  # 4 lines, 3 line breaks


def test_segment_drops_heading_blocks():
    text = "# Chapter I\n\nDark behind it rose the forest,\nBright before it beat the water,\n"
    stanzas = segment_stanzas(text)
    assert all(not s.startswith("#") for s in stanzas)
    assert len(stanzas) == 1


def test_build_index_shape():
    sources = {
        "hiawatha": {"title": "The Song of Hiawatha",
                     "url": "https://www.gutenberg.org/ebooks/19",
                     "copyright_status": "public_domain_us"},
    }
    anchors = [{
        "id": "hiawatha-antithesis",
        "source": "hiawatha",
        "locator": "Hiawatha's Childhood",
        "snippet": "Dark behind it rose the forest, / Bright before it beat the water",
        "technique": "antithetical spatial parallelism",
        "prose_translation": "two sentences with mirrored skeletons holding contrasting claims",
        "tags": ["cadence", "antithesis"],
    }]
    idx = build_index(sources, anchors, version="0.1.0")
    assert idx["version"] == "0.1.0"
    assert idx["donor"].startswith("Henry Wadsworth Longfellow")
    assert "copyright_policy" in idx
    assert idx["sources"] == sources
    assert idx["anchors"] == anchors
