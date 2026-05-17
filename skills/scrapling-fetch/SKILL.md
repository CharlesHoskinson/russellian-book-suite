---
name: scrapling-fetch
description: The sole network-touching skill of the russellian-book-suite. Wraps Scrapling 0.4.8 with arxiv, OpenAlex, Semantic Scholar HTML, and DOI adapters, plus a streaming PDF downloader. Use when you need to fetch a URL, search a paper repository, traverse a citation graph, or download a paper. Do NOT use for general scraping outside the suite — this skill is dedicated infrastructure.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: infrastructure
---

# scrapling-fetch

You are the suite's network boundary. Every outbound HTTP call from any other skill must go through you.

## Operating doctrine

1. Politeness is non-negotiable: rate limit, honor robots.txt, identify with a clear User-Agent.
2. Cache aggressively: same URL within TTL must come from disk, not network.
3. Fail typed: every terminal error maps to one of `FetchFailed | RateLimitExceeded | BlockedRequest | NotAPdf | OfflineMiss | ArxivIdNotFound`.
4. Offline mode is a first-class state (`SCRAPLING_OFFLINE=1`), not a workaround.
5. Adapters are isolated — a layout change on one site does not break the others.

## Sub-workflow routing

| Trigger | Reference | Action |
|---|---|---|
| "scrape this URL" | `references/scrapling-tuning.md` | `fetch.py` |
| "get this paper's metadata" | `references/adapter-authoring.md` | `adapters/arxiv.py` |
| "what does this paper cite" / "what cites this paper" | `references/adapter-authoring.md` | `adapters/openalex.py` (preferred), `adapters/semantic_scholar.py` (fallback) |
| "download this PDF" | `references/scrapling-tuning.md` | `download.py` |

## Public surface

See `skill_api.py`.
