from __future__ import annotations

from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file
from scripts.atom import Atom
from scripts.sort_registry import _dict_get


def test_load_symbol(fixtures_dir: Path) -> None:
    a = Atom.from_dict(read_edn_file(fixtures_dir / "valid_atom_symbol.edn"))
    assert a.kind == ":symbol"
    assert a.name == ":osmotic-pressure"
    assert a.sort.is_function()


def test_load_grounded(fixtures_dir: Path) -> None:
    a = Atom.from_dict(read_edn_file(fixtures_dir / "valid_atom_grounded.edn"))
    assert a.kind == ":grounded"
    assert a.grounded["lib"] == "z3"
    assert a.grounded["fn"] == "check_all"


def test_missing_sort_rejected(fixtures_dir: Path) -> None:
    with pytest.raises(ValueError, match="sort"):
        Atom.from_dict(read_edn_file(fixtures_dir / "invalid_atom_missing_sort.edn"))


def test_expression_atom_round_trip() -> None:
    src = {
        Keyword("kind"): Keyword("expression"),
        Keyword("sort"): Keyword("formula"),
        Keyword("head"): {Keyword("kind"): Keyword("symbol"),
                          Keyword("name"): Keyword("="),
                          Keyword("sort"): Keyword("rule")},
        Keyword("args"): [
            {Keyword("kind"): Keyword("variable"), Keyword("name"): "?x",
             Keyword("sort"): Keyword("int")},
            {Keyword("kind"): Keyword("variable"), Keyword("name"): "?x",
             Keyword("sort"): Keyword("int")},
        ],
        Keyword("doc"): "reflexivity",
        Keyword("id"): "R001",
    }
    a = Atom.from_dict(src)
    out = a.to_dict()
    # Check Keyword keys in the output
    assert _dict_get(out, "kind") == Keyword("expression")
    assert _dict_get(out, "doc") == "reflexivity"
    assert _dict_get(out, "id") == "R001"


def test_variable_atom_has_question_prefix() -> None:
    a = Atom.from_dict({Keyword("kind"): Keyword("variable"),
                        Keyword("name"): "?s",
                        Keyword("sort"): Keyword("solution")})
    assert a.is_variable()
    assert a.name.startswith("?")


def test_symbol_atom_requires_name() -> None:
    with pytest.raises(ValueError, match="symbol atom requires 'name'"):
        Atom.from_dict({Keyword("kind"): Keyword("symbol"), Keyword("sort"): Keyword("int")})


def test_grounded_atom_round_trip_preserves_meta() -> None:
    src = {
        Keyword("kind"): Keyword("grounded"),
        Keyword("sort"): Keyword("verdict"),
        Keyword("name"): ":my-fn",
        Keyword("grounded"): {Keyword("lib"): "custom", Keyword("fn"): "my_fn",
                               Keyword("napi"): True},
        Keyword("doc"): "custom solver hook",
        Keyword("id"): "G001",
        Keyword("tags"): ["experimental"],
        Keyword("force"): True,
    }
    a = Atom.from_dict(src)
    out = a.to_dict()
    assert _dict_get(out, "doc") == "custom solver hook"
    assert _dict_get(out, "id") == "G001"
    assert _dict_get(out, "tags") == ["experimental"]
    assert _dict_get(out, "force") is True
