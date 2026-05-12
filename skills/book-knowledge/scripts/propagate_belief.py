"""Bayesian belief propagation over the claim ledger's derivation graph."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import json
import shutil

from .belief_graph import BeliefGraph, prior_for_status, load_belief_graph
from .workspace import WorkspaceLayout

POSTERIOR_FLOOR = 0.05
POSTERIOR_CEIL = 0.95
COUNTER_OPEN_DAMP = 0.95
COUNTER_ADDRESSED_DAMP = 0.85
MAX_ITERATIONS = 20
CONVERGENCE_EPSILON = 1e-4


def _evidence_combine(sources: list[str], trust: dict[str, float],
                      base_prior: float) -> float:
    """1 - prod(1 - p_i*trust_i) across sources. Single source returns prior*trust."""
    if not sources:
        return base_prior
    failure = 1.0
    for s in sources:
        t = trust.get(s, 1.0)
        failure *= (1.0 - base_prior * t)
    return 1.0 - failure


def _apply_counter_damping(p: float, counter_claims_for_node: list[dict]) -> float:
    for cc in counter_claims_for_node:
        status = cc.get("status", "open")
        if status == "addressed":
            p *= COUNTER_ADDRESSED_DAMP
        elif status == "open":
            p *= COUNTER_OPEN_DAMP
        # dismissed counter-claims do not damp
    return p


def _clamp(p: float) -> float:
    return max(POSTERIOR_FLOOR, min(POSTERIOR_CEIL, p))


def propagate(graph: BeliefGraph, trust: dict[str, float],
              counter_claims: Iterable[dict]) -> dict[str, float]:
    cc_by_target: dict[str, list[dict]] = {}
    for cc in counter_claims:
        cc_by_target.setdefault(cc["target_claim_id"], []).append(cc)
    p: dict[str, float] = {}
    for cid, node in graph.nodes.items():
        p[cid] = node.p_prior if node.p_prior is not None else prior_for_status(node.status)
    for _ in range(MAX_ITERATIONS):
        new_p: dict[str, float] = {}
        for cid, node in graph.nodes.items():
            base = node.p_prior if node.p_prior is not None else prior_for_status(node.status)
            evidence = _evidence_combine(node.sources, trust, base)
            evidence = _apply_counter_damping(evidence, cc_by_target.get(cid, []))
            new_p[cid] = _clamp(evidence)
        delta = max(abs(new_p[c] - p[c]) for c in p) if p else 0.0
        p = new_p
        if delta < CONVERGENCE_EPSILON:
            break
    return p


def write_snapshot(workspace_root: Path) -> Path:
    """Write a timestamped snapshot of the claim ledger to claims/snapshots."""
    layout = WorkspaceLayout(workspace_root)
    snap_dir = layout.root / "claims" / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = snap_dir / f"{stamp}.jsonl"
    if layout.ledger.exists():
        shutil.copy2(layout.ledger, dest)
    else:
        dest.write_text("", encoding="utf-8")
    return dest


def write_posteriors(workspace_root: Path, posteriors: dict[str, float],
                     generated_by_run: str) -> int:
    layout = WorkspaceLayout(workspace_root)
    bg = load_belief_graph(workspace_root)
    written = 0
    with layout.ledger.open("a", encoding="utf-8") as fh:
        for cid, post in posteriors.items():
            node = bg.nodes.get(cid)
            if node is None:
                continue
            prior = node.p_prior if node.p_prior is not None else prior_for_status(node.status)
            latest = _latest_record_for(layout, cid)
            if latest is None:
                continue
            new = dict(latest)
            new["p_prior"] = prior
            new["p_posterior"] = post
            new["generated_by_run"] = generated_by_run
            fh.write(json.dumps(new, sort_keys=True) + "\n")
            written += 1
    return written


def _latest_record_for(layout: WorkspaceLayout, claim_id: str) -> dict | None:
    found = None
    if not layout.ledger.exists():
        return None
    for line in layout.ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec["claim_id"] == claim_id:
            found = rec
    return found
