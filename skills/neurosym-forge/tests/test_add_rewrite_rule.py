# skills/neurosym-forge/tests/test_add_rewrite_rule.py
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file
from scripts.add_rewrite_rule import add_rewrite_rule

ID_KEY = Keyword("id")
RULES_KEY = Keyword("rules")
CHECKSUMS_KEY = Keyword("checksums")
KIND_KEY = Keyword("kind")
SORT_KEY = Keyword("sort")
NAME_KEY = Keyword("name")
HEAD_KEY = Keyword("head")
ARGS_KEY = Keyword("args")
LHS_KEY = Keyword("lhs")
RHS_KEY = Keyword("rhs")
DOC_KEY = Keyword("doc")
RET_KEY = Keyword("ret")

RULE = {
    ID_KEY: "R001",
    LHS_KEY: {KIND_KEY: Keyword("expression"), SORT_KEY: Keyword("real"),
              HEAD_KEY: {KIND_KEY: Keyword("symbol"), NAME_KEY: Keyword("+"),
                         SORT_KEY: {Keyword("kind"): Keyword("fn"),
                                    Keyword("args"): [Keyword("real"), Keyword("real")],
                                    Keyword("ret"): Keyword("real")}},
              ARGS_KEY: [{KIND_KEY: Keyword("variable"), NAME_KEY: "?a", SORT_KEY: Keyword("real")},
                         {KIND_KEY: Keyword("variable"), NAME_KEY: "?b", SORT_KEY: Keyword("real")}]},
    RHS_KEY: {KIND_KEY: Keyword("expression"), SORT_KEY: Keyword("real"),
              HEAD_KEY: {KIND_KEY: Keyword("symbol"), NAME_KEY: Keyword("+"),
                         SORT_KEY: {Keyword("kind"): Keyword("fn"),
                                    Keyword("args"): [Keyword("real"), Keyword("real")],
                                    Keyword("ret"): Keyword("real")}},
              ARGS_KEY: [{KIND_KEY: Keyword("variable"), NAME_KEY: "?b", SORT_KEY: Keyword("real")},
                         {KIND_KEY: Keyword("variable"), NAME_KEY: "?a", SORT_KEY: Keyword("real")}]},
    DOC_KEY: "commutative",
}


def _seed(tmp_path: Path) -> Path:
    (tmp_path / "rules").mkdir()
    (tmp_path / "tests" / "rules").mkdir(parents=True)
    write_edn_file(tmp_path / "rules" / "seed.edn", {
        Keyword("version"): 1,
        Keyword("sorts"): [Keyword("real")],
        RULES_KEY: [],
        Keyword("atoms"): [],
    })
    write_edn_file(tmp_path / "rules" / ".checksums.edn", {CHECKSUMS_KEY: {}})
    return tmp_path


def test_appends_rule_and_fixture(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_rewrite_rule(project, RULE)
    payload = read_edn_file(project / "rules" / "seed.edn")
    assert any(r.get(ID_KEY) == "R001" for r in payload[RULES_KEY])
    assert (project / "tests" / "rules" / "test_R001.cljs").exists()


def test_rejects_duplicate_id(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_rewrite_rule(project, RULE)
    with pytest.raises(ValueError, match="duplicate rule id"):
        add_rewrite_rule(project, RULE)


def test_validates_variable_balance(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    bad = {
        ID_KEY: "R002",
        LHS_KEY: {KIND_KEY: Keyword("variable"), NAME_KEY: "?x", SORT_KEY: Keyword("real")},
        RHS_KEY: {KIND_KEY: Keyword("variable"), NAME_KEY: "?y", SORT_KEY: Keyword("real")},
    }
    with pytest.raises(ValueError, match="unbound"):
        add_rewrite_rule(project, bad)


def test_rejects_unknown_sort(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    rule = dict(RULE)
    rule[ID_KEY] = "R003"
    rule[LHS_KEY] = dict(rule[LHS_KEY])
    rule[LHS_KEY][SORT_KEY] = Keyword("nonexistent")
    with pytest.raises(ValueError, match="unknown sort"):
        add_rewrite_rule(project, rule)


def test_rejects_corrupt_seed(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    (project / "rules" / "seed.edn").write_text("not edn !!!", encoding="utf-8")
    with pytest.raises(ValueError, match="seed"):
        add_rewrite_rule(project, RULE)


def test_updates_checksum(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_rewrite_rule(project, RULE)
    checksums = read_edn_file(project / "rules" / ".checksums.edn")[CHECKSUMS_KEY]
    assert "seed.edn" in checksums
