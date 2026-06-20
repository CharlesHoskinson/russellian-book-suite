"""Cites REQ-TRIAD-004, REQ-TRIAD-005 (brief composes router+chassis+targets)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.brief import build_generation_brief

PROFILE = {"registers": {"narrative-editorial": {
    "cadence": {"p10": 4.0, "p90": 28.0, "cv": 0.55},
    "diction": {"discourse_marker_rate": 0.2, "direct_address_rate": 0.3, "example_spacing": 3.0},
    "modifier": {"p90": 0.24}}}}


def test_brief_composes_all_parts():
    b = build_generation_brief("Sending the bit, not the dossier", rotation=0, profile=PROFILE)
    assert b["register"] == "narrative-editorial"
    assert set(b["chassis"]) >= {"name", "beats"}
    assert b["targets"]["sentence_len_band"] == (4.0, 28.0)
    assert "cadence target" in b["targets_prompt"].lower()
    assert b["exemplar_query"]["register"] == "narrative-editorial"


def test_real_profile_brief_has_no_degenerate_targets():
    # builds against the REAL committed profile (no profile arg) for a technical topic,
    # which has example_spacing 0.0 -> must NOT render "every 0 sentences" / "in 0 with"
    b = build_generation_brief("How does the KZG commitment construction work?", 0)
    assert b["register"] == "technical-exposition"
    tp = b["targets_prompt"].lower()
    assert "every 0 sentences" not in tp
    assert "in 0 with" not in tp
    assert "run-on" in tp  # the speech caveat is present
