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
    r = RewriteRule.from_dict({
        "id": "R003",
        "lhs": {"kind": "expression", "sort": ":real",
                "head": {"kind": "symbol", "name": ":dup", "sort": {"kind": "fn", "args": [":real"], "ret": ":real"}},
                "args": [{"kind": "variable", "name": "?x", "sort": ":real"}]},
        "rhs": {"kind": "variable", "name": "?x", "sort": ":real"},
        "tags": ["eliminating"],
    })
    r.check_variable_balance()  # ?x bound on lhs, used on rhs, OK


def test_id_pattern_validated() -> None:
    with pytest.raises(ValueError, match="id"):
        RewriteRule.from_dict({
            "id": "badid",
            "lhs": {"kind": "variable", "name": "?x", "sort": ":real"},
            "rhs": {"kind": "variable", "name": "?x", "sort": ":real"},
        })
