"""Cites REQ-VOICE-008 (versioned ruleset selector)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.lint_common import load_rules


def test_load_rules_defaults_to_v1_frozen():
    r = load_rules()
    assert r["modifier_budget_ratio"] == 0.25  # the frozen v1 value


def test_load_rules_accepts_named_ruleset():
    r = load_rules("russellian-rules.json")  # same file, explicit
    assert "modifier_budget_ratio" in r
