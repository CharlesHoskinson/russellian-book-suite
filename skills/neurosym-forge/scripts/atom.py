"""Atom — MeTTa-style atom: symbol, variable, grounded, or expression."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from scripts.sort_registry import Sort, _dict_get, _kw_str


def _normalize(value: Any) -> Any:
    """Accept either a string or a Keyword; return the canonical form.

    For PR-1, the canonical form keeps the existing dataclass fields as
    strings so external callers comparing atom.kind == ":symbol" keep
    working. Keyword inputs from EDN are converted to their string
    representation via str(keyword).
    """
    from scripts._edn_reader import Keyword
    if isinstance(value, Keyword):
        return str(value)
    return value


@dataclass
class Atom:
    kind: str  # ":symbol" | ":variable" | ":grounded" | ":expression"
    sort: Sort
    name: Optional[str] = None
    grounded: Optional[dict[str, Any]] = None
    head: Optional["Atom"] = None
    args: list["Atom"] = field(default_factory=list)
    doc: Optional[str] = None
    id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    force: bool = False

    VALID_KINDS = (":symbol", ":variable", ":grounded", ":expression")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Atom":
        kind_raw = _dict_get(payload, "kind")
        if kind_raw is None:
            raise ValueError("atom missing 'kind'")
        kind = _normalize(kind_raw)
        if kind not in cls.VALID_KINDS:
            raise ValueError(f"unknown atom kind: {kind!r}")

        sort_raw = _dict_get(payload, "sort")
        if sort_raw is None:
            raise ValueError("atom missing 'sort'")
        sort = Sort.from_value(sort_raw)

        if kind == ":symbol":
            name_raw = _dict_get(payload, "name")
            if name_raw is None:
                raise ValueError("symbol atom requires 'name'")
            name = _normalize(name_raw)
            return cls(kind=":symbol", sort=sort, name=name,
                       doc=_dict_get(payload, "doc"),
                       id=_dict_get(payload, "id"),
                       tags=list(_dict_get(payload, "tags") or []),
                       force=bool(_dict_get(payload, "force") or False))
        if kind == ":variable":
            name_raw = _dict_get(payload, "name") or ""
            name = _normalize(name_raw) if name_raw else ""
            if not name.startswith("?"):
                raise ValueError(f"variable name must start with '?', got {name!r}")
            return cls(kind=":variable", sort=sort, name=name)
        if kind == ":grounded":
            g_raw = _dict_get(payload, "grounded")
            if not g_raw or _dict_get(g_raw, "lib") is None or _dict_get(g_raw, "fn") is None:
                raise ValueError("grounded atom requires {'grounded': {'lib', 'fn'}}")
            # Normalise grounded sub-dict to string keys for internal storage
            g = {
                "lib": _normalize(_dict_get(g_raw, "lib")),
                "fn": _normalize(_dict_get(g_raw, "fn")),
            }
            napi = _dict_get(g_raw, "napi")
            if napi is not None:
                g["napi"] = napi
            name_raw = _dict_get(payload, "name")
            name = _normalize(name_raw) if name_raw is not None else None
            return cls(kind=":grounded", sort=sort, name=name,
                       grounded=g,
                       doc=_dict_get(payload, "doc"),
                       id=_dict_get(payload, "id"),
                       tags=list(_dict_get(payload, "tags") or []),
                       force=bool(_dict_get(payload, "force") or False))
        if kind == ":expression":
            head_raw = _dict_get(payload, "head")
            args_raw = _dict_get(payload, "args")
            if head_raw is None or args_raw is None:
                raise ValueError("expression atom requires 'head' and 'args'")
            return cls(kind=":expression", sort=sort,
                       head=Atom.from_dict(head_raw),
                       args=[Atom.from_dict(a) for a in args_raw],
                       doc=_dict_get(payload, "doc"),
                       id=_dict_get(payload, "id"),
                       tags=list(_dict_get(payload, "tags") or []),
                       force=bool(_dict_get(payload, "force") or False))
        raise ValueError(f"unhandled kind {kind!r}")

    def to_dict(self) -> dict[str, Any]:
        from scripts._edn_reader import Keyword
        from scripts.sort_registry import _sort_value_to_edn
        # kind stored as ":symbol" → emit as Keyword("symbol")
        kind_val = Keyword(self.kind[1:]) if self.kind.startswith(":") else self.kind
        sort_val = _sort_value_to_edn(self.sort.value)
        out: dict[Any, Any] = {Keyword("kind"): kind_val, Keyword("sort"): sort_val}
        if self.name is not None:
            # name may be ":osmotic-pressure" (a keyword) or "?a" (a string variable)
            name_val = (Keyword(self.name[1:]) if isinstance(self.name, str) and self.name.startswith(":")
                        else self.name)
            out[Keyword("name")] = name_val
        if self.grounded is not None:
            # grounded sub-dict: convert to Keyword keys
            g: dict[Any, Any] = {}
            for k, v in self.grounded.items():
                g[Keyword(k)] = v
            out[Keyword("grounded")] = g
        if self.head is not None:
            out[Keyword("head")] = self.head.to_dict()
        if self.args:
            out[Keyword("args")] = [a.to_dict() for a in self.args]
        if self.doc is not None:
            out[Keyword("doc")] = self.doc
        if self.id is not None:
            out[Keyword("id")] = self.id
        if self.tags:
            out[Keyword("tags")] = list(self.tags)
        if self.force:
            out[Keyword("force")] = True
        return out

    def is_symbol(self) -> bool:     return self.kind == ":symbol"
    def is_variable(self) -> bool:   return self.kind == ":variable"
    def is_grounded(self) -> bool:   return self.kind == ":grounded"
    def is_expression(self) -> bool: return self.kind == ":expression"

    def free_variables(self) -> set[str]:
        if self.is_variable():
            return {self.name or ""}
        out: set[str] = set()
        if self.head is not None:
            out |= self.head.free_variables()
        for a in self.args:
            out |= a.free_variables()
        return out
