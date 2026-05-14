"""RewriteRule — a MeTTa (= lhs rhs) equality declaration."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from scripts.atom import Atom, _normalize
from scripts.sort_registry import _dict_get

ID_PATTERN = re.compile(r"^R[0-9]{3,}$")


@dataclass
class RewriteRule:
    id: str
    lhs: Atom
    rhs: Atom
    doc: str | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RewriteRule":
        rid = _normalize(_dict_get(payload, "id") or "")
        if not ID_PATTERN.match(rid):
            raise ValueError(f"rule id must match R[0-9]{{3,}}, got {rid!r}")
        lhs_raw = _dict_get(payload, "lhs")
        rhs_raw = _dict_get(payload, "rhs")
        return cls(
            id=rid,
            lhs=Atom.from_dict(lhs_raw),
            rhs=Atom.from_dict(rhs_raw),
            doc=_normalize(_dict_get(payload, "doc")),
            tags=list(_dict_get(payload, "tags") or []),
        )

    def to_dict(self) -> dict[str, Any]:
        from scripts._edn_reader import Keyword
        out: dict[Any, Any] = {
            Keyword("id"): self.id,
            Keyword("lhs"): self.lhs.to_dict(),
            Keyword("rhs"): self.rhs.to_dict(),
        }
        if self.doc is not None:
            out[Keyword("doc")] = self.doc
        if self.tags:
            out[Keyword("tags")] = list(self.tags)
        return out

    def check_variable_balance(self) -> None:
        """Every free variable on rhs must be bound on lhs.

        Unless tagged 'eliminating', lhs may not introduce variables unused on rhs.
        """
        lhs_vars = self.lhs.free_variables()
        rhs_vars = self.rhs.free_variables()
        rhs_only = rhs_vars - lhs_vars
        if rhs_only:
            raise ValueError(f"unbound variables on rhs of {self.id}: {sorted(rhs_only)}")
        if "eliminating" in self.tags:
            return
        lhs_only = lhs_vars - rhs_vars
        if lhs_only:
            raise ValueError(
                f"variables bound on lhs but unused on rhs of {self.id}: {sorted(lhs_only)}. "
                f"Tag the rule 'eliminating' if this is intentional."
            )
