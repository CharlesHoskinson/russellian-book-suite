"""Atom — MeTTa-style atom: symbol, variable, grounded, or expression."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from scripts.sort_registry import Sort


@dataclass
class Atom:
    kind: str  # "symbol" | "variable" | "grounded" | "expression"
    sort: Sort
    name: Optional[str] = None
    grounded: Optional[dict[str, Any]] = None
    head: Optional["Atom"] = None
    args: list["Atom"] = field(default_factory=list)
    doc: Optional[str] = None
    id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    force: bool = False

    VALID_KINDS = ("symbol", "variable", "grounded", "expression")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Atom":
        if "kind" not in payload:
            raise ValueError("atom missing 'kind'")
        if payload["kind"] not in cls.VALID_KINDS:
            raise ValueError(f"unknown atom kind: {payload['kind']!r}")
        if "sort" not in payload:
            raise ValueError("atom missing 'sort'")
        kind = payload["kind"]
        sort = Sort.from_value(payload["sort"])
        if kind == "symbol":
            name = payload.get("name")
            if name is None:
                raise ValueError("symbol atom requires 'name'")
            return cls(kind="symbol", sort=sort, name=name,
                       doc=payload.get("doc"), id=payload.get("id"),
                       tags=list(payload.get("tags", [])),
                       force=bool(payload.get("force", False)))
        if kind == "variable":
            name = payload.get("name", "")
            if not name.startswith("?"):
                raise ValueError(f"variable name must start with '?', got {name!r}")
            return cls(kind="variable", sort=sort, name=name)
        if kind == "grounded":
            g = payload.get("grounded")
            if not g or "lib" not in g or "fn" not in g:
                raise ValueError("grounded atom requires {'grounded': {'lib', 'fn'}}")
            return cls(kind="grounded", sort=sort, name=payload.get("name"),
                       grounded=dict(g))
        if kind == "expression":
            if "head" not in payload or "args" not in payload:
                raise ValueError("expression atom requires 'head' and 'args'")
            return cls(kind="expression", sort=sort,
                       head=Atom.from_dict(payload["head"]),
                       args=[Atom.from_dict(a) for a in payload["args"]],
                       doc=payload.get("doc"), id=payload.get("id"),
                       tags=list(payload.get("tags", [])),
                       force=bool(payload.get("force", False)))
        raise ValueError(f"unhandled kind {kind!r}")

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"kind": self.kind, "sort": self.sort.value}
        if self.name is not None:
            out["name"] = self.name
        if self.grounded is not None:
            out["grounded"] = dict(self.grounded)
        if self.head is not None:
            out["head"] = self.head.to_dict()
        if self.args:
            out["args"] = [a.to_dict() for a in self.args]
        if self.doc is not None:
            out["doc"] = self.doc
        if self.id is not None:
            out["id"] = self.id
        if self.tags:
            out["tags"] = list(self.tags)
        if self.force:
            out["force"] = True
        return out

    def is_symbol(self) -> bool:     return self.kind == "symbol"
    def is_variable(self) -> bool:   return self.kind == "variable"
    def is_grounded(self) -> bool:   return self.kind == "grounded"
    def is_expression(self) -> bool: return self.kind == "expression"

    def free_variables(self) -> set[str]:
        if self.is_variable():
            return {self.name or ""}
        out: set[str] = set()
        if self.head is not None:
            out |= self.head.free_variables()
        for a in self.args:
            out |= a.free_variables()
        return out
