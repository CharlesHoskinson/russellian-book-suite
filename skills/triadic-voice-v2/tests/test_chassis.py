"""Cites REQ-TRIAD-002 (six-archetype chassis library, rotated)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.chassis import CHASSIS, select


def test_library_has_six_archetypes():
    assert len(CHASSIS) == 6
    assert all(set(c) >= {"name", "beats"} and len(c["beats"]) >= 3 for c in CHASSIS)


def test_select_is_deterministic_and_rotates():
    a = select("narrative-editorial", 0)
    b = select("narrative-editorial", 1)
    assert a["name"] != b["name"]            # consecutive rotations differ
    assert select("narrative-editorial", 0)["name"] == a["name"]  # deterministic
