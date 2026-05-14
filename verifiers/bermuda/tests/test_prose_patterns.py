from __future__ import annotations

from scripts.prose_patterns import extract_pass_a


def test_extracts_parish_count_digit() -> None:
    atoms = extract_pass_a("Bermuda has 8 traditional parishes.")
    assert any(a["predicate"] == ":parishes-count" and a["value"] == 8 for a in atoms)


def test_extracts_parish_count_word() -> None:
    atoms = extract_pass_a("The nine parishes form the basis of local government.")
    assert any(a["predicate"] == ":parishes-count" and a["value"] == 9 for a in atoms)


def test_extracts_named_islands() -> None:
    atoms = extract_pass_a("The archipelago contains 181 named islands and rocks.")
    assert any(a["predicate"] == ":named-islands-and-rocks" and a["value"] == 181 for a in atoms)


def test_extracts_around_180_drift() -> None:
    atoms = extract_pass_a("There are around 180 islands in the chain.")
    assert any(a["predicate"] == ":named-islands-and-rocks" and a["value"] == 180 for a in atoms)


def test_no_match_returns_empty() -> None:
    assert extract_pass_a("This paragraph is unrelated.") == []


def test_each_atom_has_id_and_source_line() -> None:
    atoms = extract_pass_a("Bermuda has 8 parishes.\nLine two.", source_file="ch-02.md")
    assert atoms
    a = atoms[0]
    assert a["id"].startswith("prose-")
    assert a["source"]["file"] == "ch-02.md"
    assert a["source"]["line"] == 1
