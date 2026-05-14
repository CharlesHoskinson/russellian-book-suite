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
