"""Stage downloaded PDFs, dedup against the canonical workspace, hand off to
book-knowledge for ingest, then delete the staging copy on success.

Network and ingest are routed through skill_api modules — no direct mutation
of raw/ from this skill (NFR-5).
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from scripts.acquire.rank_candidates import ScoredCandidate

@dataclass
class IngestOutcome:
    candidate_id: str
    status: Literal["ingested", "already_present", "failed"]
    sha256: str | None = None
    reason: str | None = None

def _resolve_pdf_url(cand_id: str) -> str:
    """Map a candidate ID (arxiv:..., doi:..., etc.) to a PDF URL."""
    if cand_id.startswith("arxiv:"):
        aid = cand_id[len("arxiv:"):]
        return f"https://arxiv.org/pdf/{aid}.pdf"
    if cand_id.startswith("doi:"):
        d = cand_id[len("doi:"):]
        return f"https://doi.org/{d}"
    return cand_id  # assume already a URL

def _download_pdf(url: str, dest: Path):
    from sibling_skills import load_skill_api
    sf = load_skill_api("scrapling-fetch", expected_major=0)
    return sf.download_pdf(url, dest)

def _is_source_ingested(sha256: str, workspace_root: Path) -> bool:
    from sibling_skills import load_skill_api
    bk = load_skill_api("book-knowledge", expected_major=0)
    return bk.is_source_ingested(sha256, workspace_root)

def _ingest_pdf(source_path: Path, workspace_root: Path):
    from sibling_skills import load_skill_api
    bk = load_skill_api("book-knowledge", expected_major=0)
    return bk.ingest_pdf(source_path, workspace_root)

def download_and_ingest(candidates: list[ScoredCandidate],
                        workspace_root: Path) -> list[IngestOutcome]:
    incoming = workspace_root / "syntopical" / "acquisition" / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    outcomes: list[IngestOutcome] = []
    for cand in candidates:
        try:
            url = _resolve_pdf_url(cand.id)
            dest = incoming / f"{cand.id.replace(':', '_').replace('/', '_')}.pdf"
            dl = _download_pdf(url, dest)
            if _is_source_ingested(dl.sha256, workspace_root):
                # Already in canonical raw/ — delete staged copy and skip ingest.
                if dl.path.exists():
                    dl.path.unlink()
                outcomes.append(IngestOutcome(cand.id, "already_present", sha256=dl.sha256))
                continue
            ingest = _ingest_pdf(dl.path, workspace_root)
            if dl.path.exists() and ingest.status in {"ingested", "already_present"}:
                dl.path.unlink()
            outcomes.append(IngestOutcome(cand.id, ingest.status, sha256=ingest.sha256))
        except Exception as e:
            outcomes.append(IngestOutcome(cand.id, "failed", reason=str(e)))
    return outcomes
