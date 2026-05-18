"""arxiv.org adapter — abstract page parsing and search."""
from __future__ import annotations
from dataclasses import dataclass
from scripts.fetch import fetch
from scripts.exceptions import ArxivIdNotFound


@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str          # ISO date or "" if unparsed
    categories: list[str]
    pdf_url: str
    doi: str | None = None


@dataclass
class ArxivResult:
    arxiv_id: str
    title: str
    abstract: str


def _parse_abstract_page(arxiv_id: str, html: str) -> ArxivPaper:
    # Use Scrapling's parser
    from scrapling.parser import Adaptor
    a = Adaptor(html, "html.parser")

    # Use meta citation_title — cleaner than stripping the descriptor span from h1.
    title = a.css("meta[name='citation_title']::attr(content)").get(default="").strip()
    if not title:
        # Fallback: h1.title text, stripping the "Title:" descriptor span text.
        raw = a.css("h1.title::text").getall()
        title = " ".join(t.strip() for t in raw if t.strip() and t.strip() != "Title:").strip()
    if not title:
        raise ArxivIdNotFound(arxiv_id)

    # Authors from meta tags (citation_author); fall back to .authors a links.
    authors = a.css("meta[name='citation_author']::attr(content)").getall()
    if not authors:
        authors = [t.strip() for t in a.css(".authors a::text").getall() if t.strip()]

    # Abstract from meta tag; fall back to blockquote text stripping the descriptor.
    abstract = a.css("meta[name='citation_abstract']::attr(content)").get(default="").strip()
    if not abstract:
        raw_parts = a.css("blockquote.abstract::text").getall()
        abstract = " ".join(t.strip() for t in raw_parts if t.strip() and t.strip() != "Abstract:").strip()

    # Primary subject category.
    categories = a.css(".primary-subject::text").getall()

    return ArxivPaper(
        arxiv_id=arxiv_id,
        title=title,
        authors=[au.strip() for au in authors],
        abstract=abstract,
        published="",
        categories=categories,
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
    )


def get(arxiv_id: str) -> ArxivPaper:
    page = fetch(f"https://arxiv.org/abs/{arxiv_id}", mode="plain")
    return _parse_abstract_page(arxiv_id, page.html)


def search(query: str, max_results: int = 20) -> list[ArxivResult]:
    page = fetch(
        f"https://arxiv.org/search/?searchtype=all&query={query}&start=0",
        mode="plain",
    )
    from scrapling.parser import Adaptor
    a = Adaptor(page.html, "html.parser")
    results = []
    for li in a.css("li.arxiv-result")[:max_results]:
        aid = li.css(".list-title a::text").get(default="").replace("arXiv:", "").strip()
        title = li.css(".title::text").get(default="").strip()
        abstract = li.css(".abstract-short::text").get(default="").strip()
        if aid:
            results.append(ArxivResult(arxiv_id=aid, title=title, abstract=abstract))
    return results
