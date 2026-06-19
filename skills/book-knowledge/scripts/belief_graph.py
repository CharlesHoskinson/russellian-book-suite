"""Reads ledger.jsonl and emits an in-memory belief graph for propagation."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .io_utils import read_jsonl, latest_per
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


def load_belief_graph(workspace_root: Path) -> BeliefGraph:
    """Load belief graph from workspace ledger."""
    layout = WorkspaceLayout(workspace_root)
    records = read_jsonl(layout.ledger)
    latest = latest_per(records, "claim_id")
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


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def source_freshness_factor(
    ingested_at: str,
    as_of: str | datetime,
    *,
    half_life_days: float = 365.0,
) -> float:
    """Return deterministic age decay for a source at an explicit reference time."""
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    ingested = _parse_utc(ingested_at)
    reference = _parse_utc(as_of) if isinstance(as_of, str) else as_of
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    reference = reference.astimezone(timezone.utc)
    age_seconds = max(0.0, (reference - ingested).total_seconds())
    age_days = age_seconds / 86400.0
    return 0.5 ** (age_days / half_life_days)


def load_source_trust(
    workspace_root: Path,
    *,
    as_of: str | datetime | None = None,
    half_life_days: float = 365.0,
) -> dict[str, float]:
    """Load source trust values from manifest files.

    Reads raw/manifests/*.json files. Each manifest may carry
    {"doc_id": "...", "trust": 0.6}. Missing field defaults to 1.0.
    Missing manifest dir returns {}. When as_of is supplied, trust is
    deterministically age-discounted from the manifest ingested_at timestamp.
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
            trust = float(data.get("trust", 1.0))
            if as_of is not None and data.get("ingested_at"):
                trust *= source_freshness_factor(
                    str(data["ingested_at"]),
                    as_of,
                    half_life_days=half_life_days,
                )
            out[doc_id] = trust
    return out
