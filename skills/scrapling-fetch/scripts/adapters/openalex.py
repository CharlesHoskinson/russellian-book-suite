"""OpenAlex adapter — uses their free unauthenticated JSON API rather than HTML scraping.

JSON is strictly better than HTML for OpenAlex: structured, no layout drift,
explicit field semantics. Scrapling still mediates the HTTP request so the
suite's single-network-boundary rule (NFR-1) is preserved.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from scripts.fetch import fetch

OPENALEX_API = "https://api.openalex.org"


@dataclass
class PaperRef:
    title: str
    year: int | None = None
    citation_count: int | None = None
    openalex_id: str | None = None
    doi: str | None = None
    ss_id: str | None = None
    external_ids: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_openalex(cls, raw: dict) -> "PaperRef":
        oid = raw.get("id")
        doi = raw.get("doi", "") or ""
        # Normalize DOI by stripping the URL prefix.
        if doi.startswith("https://doi.org/"):
            doi = doi[len("https://doi.org/"):]
        ext = {}
        if doi:
            ext["doi"] = doi
        return cls(
            title=raw.get("title") or raw.get("display_name") or "",
            year=raw.get("publication_year"),
            citation_count=raw.get("cited_by_count"),
            openalex_id=oid,
            doi=doi or None,
            external_ids=ext,
        )


@dataclass
class OpenAlexWork:
    openalex_id: str
    title: str
    doi: str | None
    references: list[PaperRef]
    citations: list[PaperRef]  # filled by the .citations() call separately


def _parse_work(data: dict) -> OpenAlexWork:
    refs_raw = data.get("referenced_works", [])
    # OpenAlex referenced_works is a list of IDs in the single-work response (not expanded).
    # Return minimal PaperRefs with just the IDs; full traversal uses /works per ID.
    refs = [PaperRef(title="", openalex_id=rid) for rid in refs_raw]
    doi_raw = data.get("doi") or ""
    doi_clean = doi_raw.replace("https://doi.org/", "") or None
    return OpenAlexWork(
        openalex_id=data.get("id", ""),
        title=data.get("title", "") or data.get("display_name", ""),
        doi=doi_clean,
        references=refs,
        citations=[],
    )


def work(doi_or_id: str) -> OpenAlexWork:
    if doi_or_id.startswith("10."):
        url = f"{OPENALEX_API}/works/https://doi.org/{doi_or_id}"
    elif doi_or_id.startswith("W"):
        url = f"{OPENALEX_API}/works/{doi_or_id}"
    else:
        url = f"{OPENALEX_API}/works/{doi_or_id}"
    page = fetch(url, mode="plain")
    return _parse_work(json.loads(page.html))


def references(id_: str) -> list[PaperRef]:
    return work(id_).references


def citations(id_: str, per_page: int = 25, max_pages: int = 5) -> list[PaperRef]:
    """Fetch incoming citations to this work, paginated."""
    url = f"{OPENALEX_API}/works?filter=cites:{id_}&per-page={per_page}"
    all_refs: list[PaperRef] = []
    cursor = "*"
    for _ in range(max_pages):
        page = fetch(f"{url}&cursor={cursor}", mode="plain")
        data = json.loads(page.html)
        for item in data.get("results", []):
            all_refs.append(PaperRef.from_openalex(item))
        meta = data.get("meta", {})
        cursor = meta.get("next_cursor")
        if not cursor:
            break
    return all_refs
