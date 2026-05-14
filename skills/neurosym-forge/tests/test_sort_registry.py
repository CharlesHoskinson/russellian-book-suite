from __future__ import annotations

import pytest

from scripts.sort_registry import Sort, SortRegistry


def test_primitive_sort_validates() -> None:
    s = Sort.from_value(":int")
    assert s.is_primitive()
    assert str(s) == ":int"


def test_function_sort_validates() -> None:
    s = Sort.from_value({"kind": "fn", "args": [":int", ":real"], "ret": ":bool"})
    assert s.is_function()
    assert s.return_sort() == Sort.from_value(":bool")


def test_enum_sort_validates() -> None:
    s = Sort.from_value({"kind": "enum", "members": [":sat", ":unsat", ":unknown"]})
    assert s.is_enum()
    assert ":sat" in s.members()


def test_registry_round_trip() -> None:
    reg = SortRegistry()
    reg.add(Sort.from_value(":int"))
    reg.add(Sort.from_value(":real"))
    reg.add(Sort.from_value({"kind": "enum", "members": [":sat", ":unsat"]}))
    payload = reg.to_dict()
    reg2 = SortRegistry.from_dict(payload)
    assert reg2.contains(Sort.from_value(":int"))


def test_registry_rejects_duplicate() -> None:
    reg = SortRegistry()
    reg.add(Sort.from_value(":int"))
    with pytest.raises(ValueError, match="duplicate"):
        reg.add(Sort.from_value(":int"))


def test_registry_lookup_missing() -> None:
    reg = SortRegistry()
    assert not reg.contains(Sort.from_value(":nonexistent"))


def test_function_sort_hashable_in_set() -> None:
    a = Sort.from_value({"kind": "fn", "args": [":int", ":real"], "ret": ":bool"})
    b = Sort.from_value({"kind": "fn", "args": [":int", ":real"], "ret": ":bool"})
    c = Sort.from_value({"kind": "fn", "args": [":int"], "ret": ":bool"})
    s = {a, b, c}
    assert len(s) == 2  # a and b deduplicate; c is distinct


def test_enum_sort_hashable_in_set() -> None:
    a = Sort.from_value({"kind": "enum", "members": [":sat", ":unsat"]})
    b = Sort.from_value({"kind": "enum", "members": [":sat", ":unsat"]})
    s = {a, b}
    assert len(s) == 1


def test_primitive_sort_hashable_in_set() -> None:
    s = {Sort.from_value(":int"), Sort.from_value(":int"), Sort.from_value(":real")}
    assert len(s) == 2
