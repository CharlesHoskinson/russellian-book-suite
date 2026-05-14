from __future__ import annotations

from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file
from scripts.rewrite_rule import RewriteRule
from scripts.sort_registry import _dict_get

ID_KEY = Keyword("id")
TAGS_KEY = Keyword("tags")
LHS_KEY = Keyword("lhs")
RHS_KEY = Keyword("rhs")
KIND_KEY = Keyword("kind")
SORT_KEY = Keyword("sort")
NAME_KEY = Keyword("name")


def test_load_valid(fixtures_dir: Path) -> None:
    r = RewriteRule.from_dict(read_edn_file(fixtures_dir / "valid_rule_commutative.edn"))
    assert r.id == "R001"
    assert "commutative" in r.tags


def test_balance_check_accepts_balanced(fixtures_dir: Path) -> None:
    r = RewriteRule.from_dict(read_edn_file(fixtures_dir / "valid_rule_commutative.edn"))
    r.check_variable_balance()  # no raise


def test_balance_check_rejects_unbound_rhs(fixtures_dir: Path) -> None:
    r = RewriteRule.from_dict(read_edn_file(fixtures_dir / "invalid_rule_unbound_var.edn"))
    with pytest.raises(ValueError, match="unbound variables on rhs"):
        r.check_variable_balance()


def test_eliminating_tag_allows_lhs_drop() -> None:
    """A rule that drops ?x (used on lhs, absent on rhs) is OK with eliminating tag."""
    r = RewriteRule.from_dict({
        ID_KEY: "R003",
        LHS_KEY: {KIND_KEY: Keyword("expression"), SORT_KEY: Keyword("real"),
                  Keyword("head"): {KIND_KEY: Keyword("symbol"), NAME_KEY: Keyword("dup"),
                                    SORT_KEY: {Keyword("kind"): Keyword("fn"),
                                               Keyword("args"): [Keyword("real"), Keyword("real")],
                                               Keyword("ret"): Keyword("real")}},
                  Keyword("args"): [{KIND_KEY: Keyword("variable"), NAME_KEY: "?x",
                                     SORT_KEY: Keyword("real")},
                                    {KIND_KEY: Keyword("variable"), NAME_KEY: "?y",
                                     SORT_KEY: Keyword("real")}]},
        RHS_KEY: {KIND_KEY: Keyword("variable"), NAME_KEY: "?y", SORT_KEY: Keyword("real")},
        TAGS_KEY: ["eliminating"],
    })
    r.check_variable_balance()  # ?x is lhs-only but allowed by eliminating tag

    # And without the tag, the same shape must fail
    bad = dict(r.to_dict())
    bad[TAGS_KEY] = []
    with pytest.raises(ValueError, match="variables bound on lhs but unused on rhs"):
        RewriteRule.from_dict(bad).check_variable_balance()


def test_id_pattern_validated() -> None:
    with pytest.raises(ValueError, match="id"):
        RewriteRule.from_dict({
            ID_KEY: "badid",
            LHS_KEY: {KIND_KEY: Keyword("variable"), NAME_KEY: "?x", SORT_KEY: Keyword("real")},
            RHS_KEY: {KIND_KEY: Keyword("variable"), NAME_KEY: "?x", SORT_KEY: Keyword("real")},
        })
