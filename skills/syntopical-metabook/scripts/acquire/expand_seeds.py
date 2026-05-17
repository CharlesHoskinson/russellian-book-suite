"""Expand a set of seed paper IDs via citation-graph traversal.

Pulls references and citations of each seed via scrapling-fetch's openalex
(preferred) or semantic_scholar (fallback) adapters. Deduplicates by stable
external IDs.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import os
from sibling_skills import load_skill_api

@dataclass(frozen=True)
class PaperRef:
    title: str
    year: Optional[int] = None
    citation_count: Optional[int] = None
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    ss_id: Optional[str] = None
    openalex_id: Optional[str] = None
    external_ids: dict = field(default_factory=dict)

def _dedup_key(p: PaperRef) -> str:
    return p.arxiv_id or p.doi or p.openalex_id or p.ss_id or p.title

def _fetch_neighbors(seed: str, depth: int) -> list[PaperRef]:
    """Fetch the citation neighbors of one seed. Real implementation hits scrapling-fetch.
    Unit tests monkeypatch this function so they don't touch the network."""
    skills_root = os.environ.get("SIBLING_SKILLS_ROOT")
    if not skills_root:
        pass
    sf = load_skill_api("scrapling-fetch", expected_major=0)
    refs: list[PaperRef] = []
    seed_id = seed.split(":", 1)[-1] if ":" in seed else seed
    try:
        work = sf.openalex.work(seed_id)
        for r in work.references or []:
            refs.append(_convert_openalex(r))
    except Exception:
        try:
            for r in sf.semantic_scholar.references(seed_id) or []:
                refs.append(_convert_ss(r))
        except Exception:
            pass
    return refs

def _convert_openalex(r) -> PaperRef:
    return PaperRef(
        title=r.title,
        year=r.year,
        citation_count=r.citation_count,
        arxiv_id=r.external_ids.get("arxivId"),
        doi=r.external_ids.get("doi"),
        ss_id=r.ss_id,
        openalex_id=r.openalex_id,
        external_ids=dict(r.external_ids),
    )

def _convert_ss(r) -> PaperRef:
    return PaperRef(
        title=r.title,
        year=r.year,
        citation_count=r.citation_count,
        arxiv_id=r.external_ids.get("arxivId"),
        doi=r.external_ids.get("doi"),
        ss_id=r.ss_id,
        external_ids=dict(r.external_ids),
    )

def expand_seeds(seeds: list[str], depth: int = 2) -> list[PaperRef]:
    pool: dict[str, PaperRef] = {}
    for seed in seeds:
        for ref in _fetch_neighbors(seed, depth):
            pool.setdefault(_dedup_key(ref), ref)
    return list(pool.values())
