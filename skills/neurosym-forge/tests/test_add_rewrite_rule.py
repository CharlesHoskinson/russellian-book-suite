# skills/neurosym-forge/tests/test_add_rewrite_rule.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json, write_json_as_edn
from scripts.add_rewrite_rule import add_rewrite_rule

RULE = {
    "id": "R001",
    "lhs": {"kind": "expression", "sort": ":real",
            "head": {"kind": "symbol", "name": ":+",
                     "sort": {"kind": "fn", "args": [":real", ":real"], "ret": ":real"}},
            "args": [{"kind": "variable", "name": "?a", "sort": ":real"},
                     {"kind": "variable", "name": "?b", "sort": ":real"}]},
    "rhs": {"kind": "expression", "sort": ":real",
            "head": {"kind": "symbol", "name": ":+",
                     "sort": {"kind": "fn", "args": [":real", ":real"], "ret": ":real"}},
            "args": [{"kind": "variable", "name": "?b", "sort": ":real"},
                     {"kind": "variable", "name": "?a", "sort": ":real"}]},
    "doc": "commutative",
}


def _seed(tmp_path: Path) -> Path:
    (tmp_path / "rules").mkdir()
    (tmp_path / "tests" / "rules").mkdir(parents=True)
    write_json_as_edn(tmp_path / "rules" / "seed.edn",
                      {"version": 1, "sorts": [":real"], "rules": [], "atoms": []})
    write_json_as_edn(tmp_path / "rules" / ".checksums.edn", {"checksums": {}})
    return tmp_path


def test_appends_rule_and_fixture(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_rewrite_rule(project, RULE)
    payload = read_edn_as_json(project / "rules" / "seed.edn")
    assert any(r["id"] == "R001" for r in payload["rules"])
    assert (project / "tests" / "rules" / "test_R001.cljs").exists()


def test_rejects_duplicate_id(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_rewrite_rule(project, RULE)
    with pytest.raises(ValueError, match="duplicate rule id"):
        add_rewrite_rule(project, RULE)


def test_validates_variable_balance(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    bad = {
        "id": "R002",
        "lhs": {"kind": "variable", "name": "?x", "sort": ":real"},
        "rhs": {"kind": "variable", "name": "?y", "sort": ":real"},
    }
    with pytest.raises(ValueError, match="unbound"):
        add_rewrite_rule(project, bad)


def test_rejects_unknown_sort(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    rule = dict(RULE, id="R003")
    rule["lhs"] = dict(rule["lhs"], sort=":nonexistent")
    with pytest.raises(ValueError, match="unknown sort"):
        add_rewrite_rule(project, rule)


def test_updates_checksum(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_rewrite_rule(project, RULE)
    checksums = read_edn_as_json(project / "rules" / ".checksums.edn")["checksums"]
    assert "seed.edn" in checksums
