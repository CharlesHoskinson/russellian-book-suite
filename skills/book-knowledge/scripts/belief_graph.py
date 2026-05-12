"""Reads ledger.jsonl and emits an in-memory belief graph for propagation."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .workspace import WorkspaceLayout


PRIOR_BY_STATUS = {
    "verified":   0.70,
    "proposed":   0.50,
    "disputed":   0.20,
    "refuted":    0.05,
    "superseded": 0.50,
}


def prior_for_status(status: str) -> float:
    try:
        return PRIOR_BY_STATUS[status]
    except KeyError as e:
        raise ValueError(f"unknown status: {status!r}") from e


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


def load_source_trust(workspace_root: Path) -> dict[str, float]:
    """Load source trust values from manifest files.

    Reads raw/manifests/*.json files. Each manifest may carry
    {"doc_id": "...", "trust": 0.6}. Missing field defaults to 1.0.
    Missing manifest dir returns {}.
    """
    layout = WorkspaceLayout(workspace_root)
    manifest_dir = layout.root / "raw" / "manifests"
    out: dict[str, float] = {}
    if not manifest_dir.exists():
        return out
    for path in manifest_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        doc_id = data.get("doc_id")
        if doc_id:
            out[doc_id] = float(data.get("trust", 1.0))
    return out
