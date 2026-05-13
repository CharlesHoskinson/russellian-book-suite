"""Bayesian belief propagation over the claim ledger's derivation graph."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import json
import shutil

from .belief_graph import BeliefGraph, prior_for_status, load_belief_graph, load_source_trust
from .io_utils import read_jsonl, latest_per
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
    latest_by_id = latest_per(read_jsonl(layout.ledger), "claim_id")
    written = 0
    with layout.ledger.open("a", encoding="utf-8") as fh:
        for cid, post in posteriors.items():
            node = bg.nodes.get(cid)
            if node is None:
                continue
            prior = node.p_prior if node.p_prior is not None else prior_for_status(node.status)
            latest = latest_by_id.get(cid)
            if latest is None:
                continue
            new = dict(latest)
            new["p_prior"] = prior
            new["p_posterior"] = post
            new["generated_by_run"] = generated_by_run
            fh.write(json.dumps(new, sort_keys=True) + "\n")
            written += 1
    return written


def _histogram(values: list[float], bins: int = 10) -> list[tuple[float, float, int]]:
    if not values:
        return []
    edges = [i / bins for i in range(bins + 1)]
    counts = [0] * bins
    for v in values:
        idx = min(int(v * bins), bins - 1)
        counts[idx] += 1
    return [(edges[i], edges[i + 1], counts[i]) for i in range(bins)]


def write_report(workspace_root: Path, run_id: str,
                 before: dict[str, float], after: dict[str, float]) -> Path:
    layout = WorkspaceLayout(workspace_root)
    out_dir = layout.root / "graph" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"belief-propagation-{run_id}.md"
    deltas = sorted(
        ((cid, before.get(cid, 0.0), after[cid], after[cid] - before.get(cid, 0.0))
         for cid in after),
        key=lambda r: abs(r[3]), reverse=True,
    )
    lines = [f"# Belief propagation report — {run_id}",
             "",
             f"Total claims: {len(after)}",
             "",
             "## Top 20 absolute deltas",
             "",
             "| claim_id | before | after | delta |",
             "|---|---|---|---|"]
    for cid, b, a, d in deltas[:20]:
        lines.append(f"| {cid} | {b:.3f} | {a:.3f} | {d:+.3f} |")
    lines.append("")
    lines.append("## Posterior histogram")
    lines.append("")
    lines.append("| bin | count |")
    lines.append("|---|---|")
    for lo, hi, count in _histogram(list(after.values())):
        lines.append(f"| [{lo:.2f}, {hi:.2f}) | {count} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def run(workspace_root: Path, run_id: str | None = None) -> str:
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    write_snapshot(workspace_root)
    bg = load_belief_graph(workspace_root)
    trust = load_source_trust(workspace_root)
    # counter-claims.jsonl is append-only; later records for the same id supersede
    # earlier ones. Dedupe to latest-per-id before damping so a promoted counter-
    # claim doesn't damp twice (once as open, once as addressed).
    cc_path = WorkspaceLayout(workspace_root).root / "claims" / "counter-claims.jsonl"
    counter_claims = list(latest_per(read_jsonl(cc_path), "id").values())
    before = {cid: (n.p_posterior if n.p_posterior is not None
                    else (n.p_prior if n.p_prior is not None else prior_for_status(n.status)))
              for cid, n in bg.nodes.items()}
    after = propagate(bg, trust, counter_claims)
    write_posteriors(workspace_root, after, generated_by_run=run_id)
    write_report(workspace_root, run_id, before, after)
    return run_id


if __name__ == "__main__":
    import sys
    run(Path(sys.argv[1]))
