"""Sort registry — the type universe of the atomspace.

A Sort is either a primitive keyword (":int", ":real", ":bool", ...),
a function type {"kind": "fn", "args": [...], "ret": ...}, or an enum
{"kind": "enum", "members": [...]}.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Sort:
    value: Any  # str | dict

    @classmethod
    def from_value(cls, value: Any) -> "Sort":
        if isinstance(value, str):
            if not value.startswith(":"):
                raise ValueError(f"primitive sort must start with ':' (got {value!r})")
            return cls(value)
        if isinstance(value, dict):
            kind = value.get("kind")
            if kind == "fn":
                if "args" not in value or "ret" not in value:
                    raise ValueError("fn sort requires args and ret")
                return cls({"kind": "fn",
                            "args": [Sort.from_value(a).value for a in value["args"]],
                            "ret": Sort.from_value(value["ret"]).value})
            if kind == "enum":
                if "members" not in value or not value["members"]:
                    raise ValueError("enum sort requires non-empty members")
                return cls({"kind": "enum", "members": list(value["members"])})
            raise ValueError(f"unknown sort kind: {kind!r}")
        raise ValueError(f"sort must be str or dict, got {type(value).__name__}")

    def is_primitive(self) -> bool:
        return isinstance(self.value, str)

    def is_function(self) -> bool:
        return isinstance(self.value, dict) and self.value.get("kind") == "fn"

    def is_enum(self) -> bool:
        return isinstance(self.value, dict) and self.value.get("kind") == "enum"

    def return_sort(self) -> "Sort":
        if not self.is_function():
            raise ValueError("return_sort only valid on function sorts")
        return Sort.from_value(self.value["ret"])

    def members(self) -> list[str]:
        if not self.is_enum():
            raise ValueError("members only valid on enum sorts")
        return list(self.value["members"])

    def __str__(self) -> str:
        if isinstance(self.value, str):
            return self.value
        return str(self.value)


@dataclass
class SortRegistry:
    _sorts: list[Sort] = field(default_factory=list)

    def add(self, sort: Sort) -> None:
        if self.contains(sort):
            raise ValueError(f"duplicate sort: {sort}")
        self._sorts.append(sort)

    def contains(self, sort: Sort) -> bool:
        return any(s == sort for s in self._sorts)

    def to_dict(self) -> dict[str, Any]:
        return {"sorts": [s.value for s in self._sorts]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SortRegistry":
        reg = cls()
        for v in payload.get("sorts", []):
            reg.add(Sort.from_value(v))
        return reg
