# engine/graph.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal

Provenance = Literal["py", "agent", "human"]


@dataclass(frozen=True)
class Node:
    id: str
    text: str
    entities: tuple[str, ...] = ()        # features_computed
    role: str | None = None               # features_judged
    rationale: str | None = None          # features_judged justification
    provenance: Provenance = "agent"
    bound_slot: str | None = None
    order_index: int | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "entities": list(self.entities),
            "role": self.role,
            "rationale": self.rationale,
            "provenance": self.provenance,
            "bound_slot": self.bound_slot,
            "order_index": self.order_index,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        return cls(
            id=d["id"],
            text=d["text"],
            entities=tuple(d.get("entities", [])),
            role=d.get("role"),
            rationale=d.get("rationale"),
            provenance=d.get("provenance", "agent"),
            bound_slot=d.get("bound_slot"),
            order_index=d.get("order_index"),
        )


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: Literal["precedence"] = "precedence"
    rationale: str | None = None

    def to_dict(self) -> dict:
        return {"src": self.src, "dst": self.dst, "kind": self.kind, "rationale": self.rationale}

    @classmethod
    def from_dict(cls, d: dict) -> "Edge":
        return cls(src=d["src"], dst=d["dst"], kind=d.get("kind", "precedence"), rationale=d.get("rationale"))


@dataclass
class WeaveGraph:
    nodes: list[Node]
    edges: list[Edge] = field(default_factory=list)

    def node(self, node_id: str) -> Node:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(node_id)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in sorted(self.nodes, key=lambda n: n.id)],
            "edges": [e.to_dict() for e in sorted(self.edges, key=lambda e: (e.src, e.dst, e.kind))],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> "WeaveGraph":
        d = json.loads(s)
        return cls(
            nodes=[Node.from_dict(n) for n in d["nodes"]],
            edges=[Edge.from_dict(e) for e in d.get("edges", [])],
        )

    def content_hash(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()
