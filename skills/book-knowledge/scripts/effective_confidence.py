"""Materialize effective-confidence from the existing belief engine."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .belief_graph import (
    BeliefGraph,
    load_belief_graph,
    load_source_trust,
    prior_for_status,
)
from .io_utils import latest_per, read_jsonl
from .propagate_belief import propagate
from .workspace import WorkspaceLayout

TRUSTED_CONFLICT_THRESHOLD = 0.5
STALE_REASON_THRESHOLD = 0.95


def _parse_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _canonical_timestamp(value: str | datetime) -> str:
    return _parse_utc(value).isoformat().replace("+00:00", "Z")


def _json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def canonical_effective_confidence_rows(rows: Iterable[dict[str, Any]]) -> str:
    """Canonical JSON for result-set equality of materialized rows."""
    normalized = sorted(
        (dict(row) for row in rows),
        key=lambda row: _json(row),
    )
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))


def _prior(graph: BeliefGraph, claim_id: str) -> float:
    node = graph.nodes[claim_id]
    return float(node.p_prior if node.p_prior is not None else prior_for_status(node.status))


def _latest_claims(layout: WorkspaceLayout) -> dict[str, dict[str, Any]]:
    return latest_per(read_jsonl(layout.ledger), "claim_id")


def _latest_counter_claims(layout: WorkspaceLayout) -> list[dict[str, Any]]:
    path = layout.root / "claims" / "counter-claims.jsonl"
    return list(latest_per(read_jsonl(path), "id").values())


def _manifests(layout: WorkspaceLayout) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not layout.manifests.exists():
        return out
    for path in sorted(layout.manifests.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        doc_id = data.get("doc_id")
        if doc_id:
            out[str(doc_id)] = data
    return out


def _source_ids(record: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(span.get("doc_id"))
            for span in record.get("source_spans", [])
            if span.get("doc_id")
        }
    )


def _is_refreshed_after_source(
    source_manifest: dict[str, Any],
    target_claim: dict[str, Any],
) -> bool:
    ingested_at = source_manifest.get("ingested_at")
    created_at = target_claim.get("created_at")
    if not ingested_at or not created_at:
        return False
    try:
        return _parse_utc(str(ingested_at)) > _parse_utc(str(created_at))
    except ValueError:
        return False


def _trusted_conflict_counter_claims(
    layout: WorkspaceLayout,
    latest_claims: dict[str, dict[str, Any]],
    decayed_trust: dict[str, float],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, str]]]]:
    """Convert fresh trusted conflict edges into engine counter-claim inputs."""
    manifests = _manifests(layout)
    synthetic: list[dict[str, Any]] = []
    reasons: dict[str, list[dict[str, str]]] = {}
    for conflict_id, conflict_claim in sorted(latest_claims.items()):
        targets = sorted(str(target) for target in conflict_claim.get("conflicts_with", []))
        if not targets:
            continue
        for target_id in targets:
            target_claim = latest_claims.get(target_id)
            if target_claim is None:
                continue
            for source_id in _source_ids(conflict_claim):
                manifest = manifests.get(source_id)
                if manifest is None:
                    continue
                if decayed_trust.get(source_id, 1.0) < TRUSTED_CONFLICT_THRESHOLD:
                    continue
                if not _is_refreshed_after_source(manifest, target_claim):
                    continue
                synthetic.append(
                    {
                        "id": f"conflict:{conflict_id}:{target_id}:{source_id}",
                        "target_claim_id": target_id,
                        "status": "open",
                    }
                )
                reasons.setdefault(target_id, []).append(
                    {
                        "kind": "refreshed-source-conflict",
                        "source_id": source_id,
                        "conflict_claim_id": conflict_id,
                    }
                )
    return synthetic, {key: sorted(value, key=_json) for key, value in reasons.items()}


def _parents_by_child(graph: BeliefGraph) -> dict[str, list[str]]:
    parents: dict[str, list[str]] = {}
    for parent, child in graph.derivation_edges:
        parents.setdefault(child, []).append(parent)
    return {child: sorted(values) for child, values in parents.items()}


def _counter_reasons(counter_claims: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    reasons: dict[str, list[dict[str, str]]] = {}
    for cc in sorted(counter_claims, key=lambda row: str(row.get("id", ""))):
        status = str(cc.get("status", "open"))
        if status == "dismissed":
            continue
        target = cc.get("target_claim_id")
        if target is None:
            continue
        reasons.setdefault(str(target), []).append(
            {"kind": "counter-claim", "id": str(cc.get("id")), "status": status}
        )
    return reasons


def _parent_reason(
    graph: BeliefGraph,
    posteriors: dict[str, float],
    parents_by_child: dict[str, list[str]],
    claim_id: str,
) -> list[dict[str, str]]:
    candidates: list[tuple[float, str]] = []
    for parent in parents_by_child.get(claim_id, []):
        if parent not in graph.nodes:
            continue
        parent_prior = _prior(graph, parent)
        parent_post = posteriors.get(parent, parent_prior)
        if parent_post < parent_prior:
            candidates.append((parent_post, parent))
    if not candidates:
        return []
    _, parent_id = sorted(candidates, key=lambda item: (item[0], item[1]))[0]
    return [{"kind": "weakened-parent", "claim_id": parent_id}]


def _freshness_factor(
    sources: list[str],
    raw_trust: dict[str, float],
    decayed_trust: dict[str, float],
) -> float:
    if not sources:
        return 1.0
    factors: list[float] = []
    for source_id in sources:
        raw = raw_trust.get(source_id, 1.0)
        decayed = decayed_trust.get(source_id, raw)
        factors.append(decayed / raw if raw > 0 else 0.0)
    return min(factors) if factors else 1.0


def _stale_source_reasons(
    sources: list[str],
    raw_trust: dict[str, float],
    decayed_trust: dict[str, float],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for source_id in sources:
        raw = raw_trust.get(source_id, 1.0)
        if raw <= 0:
            continue
        factor = decayed_trust.get(source_id, raw) / raw
        if factor < STALE_REASON_THRESHOLD:
            out.append({"kind": "stale-source", "source_id": source_id})
    return out


def materialize_effective_confidence(
    layout: WorkspaceLayout | Path,
    store,
    *,
    as_of: str | datetime,
    half_life_days: float = 365.0,
) -> list[dict[str, Any]]:
    """Materialize effective-confidence rows without modifying the ledger."""
    layout = layout if isinstance(layout, WorkspaceLayout) else WorkspaceLayout(Path(layout))
    as_of_text = _canonical_timestamp(as_of)
    graph = load_belief_graph(layout.root)
    latest_claims = _latest_claims(layout)
    raw_trust = load_source_trust(layout.root)
    decayed_trust = load_source_trust(
        layout.root,
        as_of=as_of_text,
        half_life_days=half_life_days,
    )
    counter_claims = _latest_counter_claims(layout)
    synthetic_conflicts, conflict_reasons = _trusted_conflict_counter_claims(
        layout,
        latest_claims,
        decayed_trust,
    )
    engine_counter_claims = counter_claims + synthetic_conflicts
    posteriors = propagate(graph, decayed_trust, engine_counter_claims)

    cc_reasons = _counter_reasons(counter_claims)
    parents = _parents_by_child(graph)
    rows: list[dict[str, Any]] = []
    for claim_id in sorted(graph.nodes):
        node = graph.nodes[claim_id]
        prior = _prior(graph, claim_id)
        posterior = float(posteriors[claim_id])
        sources = sorted(node.sources)
        freshness = _freshness_factor(sources, raw_trust, decayed_trust)
        reasons: list[dict[str, str]] = []
        if posterior < prior:
            reasons.extend(cc_reasons.get(claim_id, []))
            reasons.extend(_parent_reason(graph, posteriors, parents, claim_id))
            reasons.extend(conflict_reasons.get(claim_id, []))
            reasons.extend(_stale_source_reasons(sources, raw_trust, decayed_trust))
        row = {
            "id": claim_id,
            "claim_id": claim_id,
            "prior": round(prior, 12),
            "posterior": round(posterior, 12),
            "effective": round(posterior, 12),
            "freshness_factor": round(freshness, 12),
            "support_erosion_reason": reasons,
            "support_erosion_reason_json": _json(reasons),
            "as_of": as_of_text,
        }
        rows.append(row)
    store.load("effective-confidence", rows)
    return rows


def _claim_witnesses(record: dict[str, Any]) -> list[dict[str, str]]:
    witnesses: list[dict[str, str]] = []
    for parent in sorted(str(cid) for cid in record.get("derived_from", [])):
        witnesses.append({"kind": "parent-claim", "id": parent})
    for source_id in _source_ids(record):
        witnesses.append({"kind": "source", "id": source_id})
    return witnesses


def compute_why_provenance(
    layout: WorkspaceLayout | Path,
    *,
    flagged_claim_ids: Iterable[str],
    bound: int = 8,
    cache: bool = True,
) -> dict[str, dict[str, Any]]:
    """Compute bounded why-provenance only for flagged load-bearing claims."""
    if bound < 0:
        raise ValueError("bound must be non-negative")
    layout = layout if isinstance(layout, WorkspaceLayout) else WorkspaceLayout(Path(layout))
    latest = _latest_claims(layout)
    out: dict[str, dict[str, Any]] = {}
    for claim_id in sorted(set(flagged_claim_ids)):
        record = latest.get(claim_id)
        if record is None or not bool(record.get("load_bearing", False)):
            continue
        witnesses = _claim_witnesses(record)
        row = {
            "claim_id": claim_id,
            "witnesses": witnesses[:bound],
            "truncated": len(witnesses) > bound,
            "bound": bound,
        }
        out[claim_id] = row

    if cache and out:
        cache_path = layout.root / "claims" / "why-provenance.jsonl"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("a", encoding="utf-8") as fh:
            for row in out.values():
                fh.write(json.dumps(row, sort_keys=True) + "\n")
    return out
