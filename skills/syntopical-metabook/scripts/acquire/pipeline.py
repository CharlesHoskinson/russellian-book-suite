"""Full acquire pipeline: expand_seeds → rank → triage → apply_veto → download_and_ingest.

Convenience entry point for running all acquire steps in sequence.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AcquireResult:
    expanded: list = field(default_factory=list)
    scored: list = field(default_factory=list)
    triage_result: Any = None
    veto_result: Any = None
    ingest_outcomes: list = field(default_factory=list)


def run_acquire(
    seeds: list[str],
    query_text: str,
    workspace_root: Path,
    run_id: str,
    thesis_tree: Any = None,
    depth: int = 2,
) -> AcquireResult:
    """Run the full acquire pipeline end-to-end.

    Steps: expand_seeds → rank → triage → apply_veto → download_and_ingest.
    Returns an AcquireResult bundling outputs of each stage.
    """
    from scripts.acquire.expand_seeds import expand_seeds
    from scripts.acquire.rank_candidates import rank, Candidate
    from scripts.acquire.triage import triage, TriageConfig
    from scripts.acquire.veto import apply_veto
    from scripts.acquire.download_and_ingest import download_and_ingest

    expanded = expand_seeds(seeds, depth=depth)

    candidates = [
        Candidate(
            id=getattr(p, "arxiv_id", None) or getattr(p, "doi", None) or p.title,
            title=p.title,
            abstract="",
        )
        for p in expanded
    ]
    scored = rank(query_text, candidates) if candidates else []

    cfg = TriageConfig()
    triage_result = triage(scored, cfg, workspace_root, run_id)

    candidate_lookup = {c.id: c for c in scored}
    manifest_path = workspace_root / "syntopical" / "acquisition" / f"manifest-{run_id}.json"
    veto_result = apply_veto(triage_result, thesis_tree, candidate_lookup, manifest_path)

    ingest_outcomes = download_and_ingest(veto_result.auto_approve, workspace_root)

    return AcquireResult(
        expanded=expanded,
        scored=scored,
        triage_result=triage_result,
        veto_result=veto_result,
        ingest_outcomes=ingest_outcomes,
    )
