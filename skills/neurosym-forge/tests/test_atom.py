from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json
from scripts.atom import Atom


def test_load_symbol(fixtures_dir: Path) -> None:
    a = Atom.from_dict(read_edn_as_json(fixtures_dir / "valid_atom_symbol.edn"))
    assert a.kind == "symbol"
    assert a.name == ":osmotic-pressure"
    assert a.sort.is_function()


def test_load_grounded(fixtures_dir: Path) -> None:
    a = Atom.from_dict(read_edn_as_json(fixtures_dir / "valid_atom_grounded.edn"))
    assert a.kind == "grounded"
    assert a.grounded["lib"] == "z3"
    assert a.grounded["fn"] == "check_all"


def test_missing_sort_rejected(fixtures_dir: Path) -> None:
    with pytest.raises(ValueError, match="sort"):
        Atom.from_dict(read_edn_as_json(fixtures_dir / "invalid_atom_missing_sort.edn"))


def test_expression_atom_round_trip() -> None:
    src = {
        "kind": "expression",
        "sort": ":formula",
        "head": {"kind": "symbol", "name": ":=", "sort": ":rule"},
        "args": [
            {"kind": "variable", "name": "?x", "sort": ":int"},
            {"kind": "variable", "name": "?x", "sort": ":int"},
        ],
        "doc": "reflexivity",
        "id": "R001",
    }
    a = Atom.from_dict(src)
    assert a.to_dict() == src


def test_variable_atom_has_question_prefix() -> None:
    a = Atom.from_dict({"kind": "variable", "name": "?s", "sort": ":solution"})
    assert a.is_variable()
    assert a.name.startswith("?")
