"""Reads ledger.jsonl and emits an in-memory belief graph for propagation."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .workspace import WorkspaceLayout


@dataclass
class BeliefNode:
    claim_id: str
    status: str
    sources: list[str] = field(default_factory=list)
    p_prior: float | None = None
    p_posterior: float | None = None
    counter_claim_ids: list[str] = field(default_factory=list)
    load_bearing: bool = False


@dataclass
class BeliefGraph:
    nodes: dict[str, BeliefNode] = field(default_factory=dict)
    derivation_edges: set[tuple[str, str]] = field(default_factory=set)  # (parent, child)


def _latest_per_claim(records: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for r in records:
        latest[r["claim_id"]] = r
    return latest


def load_belief_graph(workspace_root: Path) -> BeliefGraph:
    """Load belief graph from workspace ledger."""
    layout = WorkspaceLayout(workspace_root)
    records: list[dict] = []
    if layout.ledger.exists():
        for line in layout.ledger.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    latest = _latest_per_claim(records)
    g = BeliefGraph()
    for cid, rec in latest.items():
        g.nodes[cid] = BeliefNode(
            claim_id=cid,
            status=rec["status"],
            sources=[s["doc_id"] for s in rec.get("source_spans", [])],
            p_prior=rec.get("p_prior"),
            p_posterior=rec.get("p_posterior"),
            counter_claim_ids=list(rec.get("counter_claim_ids", [])),
            load_bearing=bool(rec.get("load_bearing", False)),
        )
        for parent in rec.get("derived_from", []):
            g.derivation_edges.add((parent, cid))
    return g
