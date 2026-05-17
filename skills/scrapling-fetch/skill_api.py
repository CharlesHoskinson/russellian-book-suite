from __future__ import annotations

API_VERSION = (0, 1)

from scripts.fetch import fetch, Page
from scripts.download import download_pdf, DownloadResult
from scripts.exceptions import (
    FetchFailed, RateLimitExceeded, BlockedRequest,
    NotAPdf, OfflineMiss, ArxivIdNotFound,
)
from scripts.adapters import arxiv, openalex, semantic_scholar, doi

__all__ = [
    "fetch", "Page",
    "download_pdf", "DownloadResult",
    "FetchFailed", "RateLimitExceeded", "BlockedRequest",
    "NotAPdf", "OfflineMiss", "ArxivIdNotFound",
    "arxiv", "openalex", "semantic_scholar", "doi",
]
