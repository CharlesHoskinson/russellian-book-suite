"""DOI resolver — follows the redirect from doi.org and returns the final URL."""
from __future__ import annotations
from dataclasses import dataclass
from scripts.fetch import fetch


@dataclass
class ResolvedDoi:
    final_url: str
    publisher: str | None
    free_pdf_url: str | None


def _fetch_doi(doi: str):
    return fetch(f"https://doi.org/{doi}", mode="plain")


def resolve(doi: str) -> ResolvedDoi:
    page = _fetch_doi(doi)
    publisher = None
    if "springer" in page.final_url:
        publisher = "springer"
    elif "elsevier" in page.final_url or "sciencedirect" in page.final_url:
        publisher = "elsevier"
    return ResolvedDoi(
        final_url=page.final_url,
        publisher=publisher,
        free_pdf_url=None,
    )
