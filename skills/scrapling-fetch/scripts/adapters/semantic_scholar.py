"""Semantic Scholar adapter — scrapes the public paper page (used as fallback for openalex).

Uses Scrapling's StealthySession because plain requests are often blocked.
"""
from __future__ import annotations
from scripts.fetch import fetch
from scripts.adapters.openalex import PaperRef

SS_BASE = "https://www.semanticscholar.org/paper"


def _fetch(url: str):
    return fetch(url, mode="stealth")


def _parse_refs(html: str) -> list[PaperRef]:
    from scrapling.parser import Adaptor
    a = Adaptor(html, "html.parser")
    refs = []
    for row in a.css("[data-test='paper-row']"):
        title = row.css("[data-test='paper-title']::text").get(default="").strip()
        year_raw = row.css("[data-test='year']::text").get(default="").strip()
        cc_raw = row.css("[data-test='citation-count']::text").get(default="").strip()
        if title:
            refs.append(PaperRef(
                title=title,
                year=int(year_raw) if year_raw.isdigit() else None,
                citation_count=int(cc_raw) if cc_raw.isdigit() else None,
            ))
    return refs


def references(id_or_url: str) -> list[PaperRef]:
    url = id_or_url if id_or_url.startswith("http") else f"{SS_BASE}/{id_or_url}"
    if not url.endswith("/references"):
        url = url.rstrip("/") + "/references"
    return _parse_refs(_fetch(url).html)


def citations(id_or_url: str) -> list[PaperRef]:
    url = id_or_url if id_or_url.startswith("http") else f"{SS_BASE}/{id_or_url}"
    if not url.endswith("/citations"):
        url = url.rstrip("/") + "/citations"
    return _parse_refs(_fetch(url).html)
