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
