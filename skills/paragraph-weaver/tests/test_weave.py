from __future__ import annotations

import pytest
pytestmark = pytest.mark.windows_canary

from engine.weave import validate_bridge, validate_seam_edit, load_relations


def test_relations_load_from_asset():
    rels = load_relations()
    assert "contrast" in rels and "elaboration" in rels


def test_bridge_ok_when_entities_subset_and_relation_allowed():
    res = validate_bridge(
        "This shell is a spiral.",
        left_entities=("shell", "snails"),
        right_entities=("shell", "spiral"),
        relation="elaboration",
    )
    assert res.ok, res.reasons


def test_bridge_rejected_for_new_entity():
    res = validate_bridge(
        "Therefore octopuses exist.",
        left_entities=("shell",),
        right_entities=("spiral",),
        relation="contrast",
    )
    assert not res.ok
    assert any("octopuses" in r for r in res.reasons)


def test_bridge_rejected_for_unknown_relation():
    res = validate_bridge(
        "This shell is a spiral.",
        left_entities=("shell",),
        right_entities=("spiral",),
        relation="teleportation",
    )
    assert not res.ok
    assert any("relation" in r for r in res.reasons)


def test_seam_edit_ok_when_load_bearing_tokens_survive():
    res = validate_seam_edit("It hardens into a calcareous shell.", load_bearing_tokens=["shell"])
    assert res.ok and res.missing == []


def test_seam_edit_rejected_when_token_deleted():
    res = validate_seam_edit("It simply hardens.", load_bearing_tokens=["shell"])
    assert not res.ok
    assert res.missing == ["shell"]
