# tests/test_skill_api.py
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import skill_api


def test_api_version():
    assert skill_api.API_VERSION == (0, 1)


def test_three_targets_registered():
    names = set(skill_api.REGISTRY)
    assert {"argument", "emotion", "narrative"} <= names


def test_argument_is_deep_others_shallow():
    assert skill_api.get_target("argument").depth == "deep"
    assert skill_api.get_target("emotion").depth == "shallow"
    assert skill_api.get_target("narrative").depth == "shallow"


def test_core_callables_exposed():
    for name in ("extract_entities", "find_cycles", "check_feasibility",
                 "order_paragraphs", "validate_bridge", "validate_seam_edit",
                 "score_gate", "render_provenance", "WeaveGraph"):
        assert hasattr(skill_api, name), name
