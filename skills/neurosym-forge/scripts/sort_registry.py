"""Sort registry — the type universe of the atomspace.

A Sort is either a primitive keyword (":int", ":real", ":bool", ...),
a function type {"kind": "fn", "args": [...], "ret": ...}, or an enum
{"kind": "enum", "members": [...]}.

PR-1 migration note: Sort.from_value now accepts EDN Keyword instances as
primitive sorts (e.g. Keyword("int") is treated as ":int"). Dict sorts accept
either string keys or Keyword keys.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _is_keyword(v: Any) -> bool:
    """Duck-type check for Keyword: has .name attr and str() starts with ':'."""
    return hasattr(v, "name") and not isinstance(v, type) and str(v).startswith(":")


def _kw_str(k: Any) -> str:
    """Return str(k) if k is a Keyword-like object, else k unchanged."""
    return str(k) if _is_keyword(k) else k


def _dict_get(d: dict, name: str) -> Any:
    """Get from dict by string key or Keyword key with matching .name."""
    if name in d:
        return d[name]
    for k, v in d.items():
        if _is_keyword(k) and k.name == name:
            return v
    return None


@dataclass(frozen=True)
class Sort:
    value: Any  # str | dict

    @classmethod
    def from_value(cls, value: Any) -> "Sort":
        # Accept EDN Keyword as a primitive sort: Keyword("int") → Sort(":int")
        if _is_keyword(value):
            return cls(str(value))
        if isinstance(value, str):
            if not value.startswith(":"):
                raise ValueError(f"primitive sort must start with ':' (got {value!r})")
            return cls(value)
        if isinstance(value, dict):
            # Accept either string keys or Keyword keys
            kind_raw = _dict_get(value, "kind")
            kind = _kw_str(kind_raw) if kind_raw is not None else None
            if kind in (":fn", "fn"):
                args = _dict_get(value, "args")
                ret = _dict_get(value, "ret")
                if args is None or ret is None:
                    raise ValueError("fn sort requires args and ret")
                return cls({"kind": "fn",
                            "args": [Sort.from_value(a).value for a in args],
                            "ret": Sort.from_value(ret).value})
            if kind in (":enum", "enum"):
                members = _dict_get(value, "members")
                if not members:
                    raise ValueError("enum sort requires non-empty members")
                return cls({"kind": "enum", "members": list(members)})
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

    def __hash__(self) -> int:
        if isinstance(self.value, str):
            return hash(("primitive", self.value))
        kind = self.value.get("kind")
        if kind == "fn":
            return hash(("fn", tuple(self.value["args"]), self.value["ret"]))
        if kind == "enum":
            return hash(("enum", tuple(self.value["members"])))
        return hash(str(self.value))

    def __str__(self) -> str:
        if isinstance(self.value, str):
            return self.value
        return str(self.value)


def _sort_value_to_edn(v: Any) -> Any:
    """Convert a Sort.value to an EDN-friendly form.

    Primitive sorts stored as ":int" strings are converted to Keyword("int")
    so the EDN writer emits :int rather than ":int". Compound sorts (dicts
    with string keys) are converted to use Keyword keys so the EDN file uses
    real keywords throughout.
    """
    from scripts._edn_reader import Keyword  # local import to avoid circular at module load
    if isinstance(v, str) and v.startswith(":"):
        return Keyword(v[1:])
    if isinstance(v, dict):
        out: dict[Any, Any] = {}
        for k, val in v.items():
            edn_key = Keyword(k) if isinstance(k, str) else k
            if k == "kind" and isinstance(val, str):
                out[edn_key] = Keyword(val)
            elif k in ("args", "members") and isinstance(val, list):
                out[edn_key] = [_sort_value_to_edn(a) for a in val]
            elif k == "ret":
                out[edn_key] = _sort_value_to_edn(val)
            else:
                out[edn_key] = val
        return out
    return v


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

    def to_edn_sorts(self) -> list[Any]:
        """Return sorts as EDN-friendly values (primitive sorts as Keywords)."""
        return [_sort_value_to_edn(s.value) for s in self._sorts]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SortRegistry":
        reg = cls()
        sorts = _dict_get(payload, "sorts") or []
        for v in sorts:
            reg.add(Sort.from_value(v))
        return reg
