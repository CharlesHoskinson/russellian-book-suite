from __future__ import annotations

from pathlib import Path

from scripts._edn_reader import Keyword
from scripts.prose_patterns import extract_pass_a

_KW_PREDICATE = Keyword("predicate")
_KW_VALUE = Keyword("value")
_KW_ID = Keyword("id")
_KW_SOURCE = Keyword("source")


def test_extracts_parish_count_digit() -> None:
    atoms = extract_pass_a("Bermuda has 8 traditional parishes.")
    assert any(a[_KW_PREDICATE] == ":parishes-count" and a[_KW_VALUE] == 8 for a in atoms)


def test_extracts_parish_count_word() -> None:
    atoms = extract_pass_a("The nine parishes form the basis of local government.")
    assert any(a[_KW_PREDICATE] == ":parishes-count" and a[_KW_VALUE] == 9 for a in atoms)


def test_extracts_named_islands() -> None:
    atoms = extract_pass_a("The archipelago contains 181 named islands and rocks.")
    assert any(a[_KW_PREDICATE] == ":named-islands-and-rocks" and a[_KW_VALUE] == 181 for a in atoms)


def test_extracts_around_180_drift() -> None:
    atoms = extract_pass_a("There are around 180 islands in the chain.")
    assert any(a[_KW_PREDICATE] == ":named-islands-and-rocks" and a[_KW_VALUE] == 180 for a in atoms)


def test_no_match_returns_empty() -> None:
    assert extract_pass_a("This paragraph is unrelated.") == []


def test_each_atom_has_id_and_source_line() -> None:
    atoms = extract_pass_a("Bermuda has 8 parishes.\nLine two.", source_file="ch-02.md")
    assert atoms
    a = atoms[0]
    assert a[_KW_ID].startswith("prose-")
    assert a[_KW_SOURCE]["file"] == "ch-02.md"
    assert a[_KW_SOURCE]["line"] == 1
