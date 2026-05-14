"""RewriteRule — a MeTTa (= lhs rhs) equality declaration."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from scripts.atom import Atom

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
        rid = payload.get("id", "")
        if not ID_PATTERN.match(rid):
            raise ValueError(f"rule id must match R[0-9]{{3,}}, got {rid!r}")
        return cls(
            id=rid,
            lhs=Atom.from_dict(payload["lhs"]),
            rhs=Atom.from_dict(payload["rhs"]),
            doc=payload.get("doc"),
            tags=list(payload.get("tags", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "lhs": self.lhs.to_dict(),
            "rhs": self.rhs.to_dict(),
        }
        if self.doc is not None:
            out["doc"] = self.doc
        if self.tags:
            out["tags"] = list(self.tags)
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
