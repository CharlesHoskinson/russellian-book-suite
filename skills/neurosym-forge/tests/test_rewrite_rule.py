from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json
from scripts.rewrite_rule import RewriteRule


def test_load_valid(fixtures_dir: Path) -> None:
    r = RewriteRule.from_dict(read_edn_as_json(fixtures_dir / "valid_rule_commutative.edn"))
    assert r.id == "R001"
    assert "commutative" in r.tags


def test_balance_check_accepts_balanced(fixtures_dir: Path) -> None:
    r = RewriteRule.from_dict(read_edn_as_json(fixtures_dir / "valid_rule_commutative.edn"))
    r.check_variable_balance()  # no raise


def test_balance_check_rejects_unbound_rhs(fixtures_dir: Path) -> None:
    r = RewriteRule.from_dict(read_edn_as_json(fixtures_dir / "invalid_rule_unbound_var.edn"))
    with pytest.raises(ValueError, match="unbound variables on rhs"):
        r.check_variable_balance()


def test_eliminating_tag_allows_lhs_drop() -> None:
    """A rule that drops ?x (used on lhs, absent on rhs) is OK with eliminating tag."""
    r = RewriteRule.from_dict({
        "id": "R003",
        "lhs": {"kind": "expression", "sort": ":real",
                "head": {"kind": "symbol", "name": ":dup",
                         "sort": {"kind": "fn", "args": [":real", ":real"], "ret": ":real"}},
                "args": [{"kind": "variable", "name": "?x", "sort": ":real"},
                         {"kind": "variable", "name": "?y", "sort": ":real"}]},
        "rhs": {"kind": "variable", "name": "?y", "sort": ":real"},
        "tags": ["eliminating"],
    })
    r.check_variable_balance()  # ?x is lhs-only but allowed by eliminating tag

    # And without the tag, the same shape must fail
    bad = dict(r.to_dict())
    bad["tags"] = []
    with pytest.raises(ValueError, match="variables bound on lhs but unused on rhs"):
        RewriteRule.from_dict(bad).check_variable_balance()


def test_id_pattern_validated() -> None:
    with pytest.raises(ValueError, match="id"):
        RewriteRule.from_dict({
            "id": "badid",
            "lhs": {"kind": "variable", "name": "?x", "sort": ":real"},
            "rhs": {"kind": "variable", "name": "?x", "sort": ":real"},
        })
