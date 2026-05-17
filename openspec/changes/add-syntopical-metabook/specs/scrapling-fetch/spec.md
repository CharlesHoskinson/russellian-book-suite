# Scrapling Fetch — Added Requirements

## ADDED Requirements

### Requirement: Generic Fetch Interface
The scrapling-fetch skill SHALL expose
`fetch(url: str, mode: Literal["plain","stealth","dynamic"] = "plain", timeout_s: int = 20) -> Page`
where `Page` is a dataclass with fields: url, final_url, status, html,
fetched_at, headers.

#### Scenario: Plain mode fetch returns populated Page
- GIVEN a static HTML URL and mode="plain"
- WHEN `fetch` is called
- THEN `Page.status == 200` and `Page.html` is non-empty

#### Scenario: Dynamic mode renders JS-rendered content
- GIVEN a JS-rendered page and mode="dynamic"
- WHEN `fetch` is called
- THEN `Page.html` contains content not present in the raw network HTML

---

### Requirement: Fetcher Mode Selection
The scrapling-fetch skill SHALL select the underlying Scrapling fetcher per
mode: `Fetcher` for "plain", `StealthyFetcher` for "stealth",
`DynamicFetcher` for "dynamic".

#### Scenario: Plain mode uses Fetcher
- GIVEN mode="plain"
- WHEN `fetch` is called
- THEN the Scrapling `Fetcher` class handles the request

#### Scenario: Stealth mode uses StealthyFetcher
- GIVEN mode="stealth"
- WHEN `fetch` is called
- THEN the Scrapling `StealthyFetcher` class handles the request

---

### Requirement: Session Configuration with Cache and Rate Limiting
The scrapling-fetch skill SHALL configure Scrapling's built-in per-host
download_delay, response cache, and robots_txt_obey=True at session
construction. The cache root SHALL be `~/.cache/scrapling-fetch/`.

#### Scenario: Cache directory is created under user home
- GIVEN a fresh installation with no prior cache
- WHEN a session is constructed
- THEN the directory `~/.cache/scrapling-fetch/` is created and used as the cache root

#### Scenario: robots.txt is obeyed by default
- GIVEN a host with a robots.txt disallowing crawling
- WHEN a session is constructed
- THEN `robots_txt_obey=True` is set and the fetcher respects disallow directives

---

### Requirement: Typed Error Wrapping
The scrapling-fetch skill SHALL wrap terminal errors in typed exceptions from
the set {FetchFailed, RateLimitExceeded, BlockedRequest, NotAPdf, OfflineMiss}
and re-raise when Scrapling raises a terminal error after its built-in retries.

#### Scenario: Terminal network error wrapped as FetchFailed
- GIVEN a URL that causes Scrapling to exhaust all built-in retries
- WHEN `fetch` is called
- THEN a `FetchFailed` exception is raised (not a raw Scrapling exception)

#### Scenario: Rate-limit response wrapped as RateLimitExceeded
- GIVEN a host that returns a 429 response after retries
- WHEN `fetch` is called
- THEN a `RateLimitExceeded` exception is raised

---

### Requirement: Offline Cache-Only Mode
Where `SCRAPLING_OFFLINE=1` is set, the scrapling-fetch skill SHALL serve only
from cache and SHALL raise `OfflineMiss` on cache miss.

#### Scenario: Cached URL served in offline mode
- GIVEN `SCRAPLING_OFFLINE=1` is set and the URL is present in the cache
- WHEN `fetch` is called
- THEN the cached response is returned with no network request

#### Scenario: Cache miss raises OfflineMiss in offline mode
- GIVEN `SCRAPLING_OFFLINE=1` is set and the URL is not in the cache
- WHEN `fetch` is called
- THEN `OfflineMiss` is raised

---

### Requirement: arXiv Adapter
The scrapling-fetch skill SHALL expose `arxiv.search(query: str, max_results: int = 20) -> List[ArxivResult]`
and `arxiv.get(arxiv_id: str) -> ArxivPaper` returning dataclasses with
fields: arxiv_id, title, authors, abstract, published, categories, pdf_url,
and optional doi.

#### Scenario: Valid arxiv ID returns fully populated ArxivPaper
- GIVEN a valid arxiv ID
- WHEN `arxiv.get` is called
- THEN every required field of `ArxivPaper` is non-empty

#### Scenario: Unknown arxiv ID raises ArxivIdNotFound
- GIVEN an arxiv ID that does not exist
- WHEN `arxiv.get` is called
- THEN `ArxivIdNotFound` is raised

---

### Requirement: OpenAlex Adapter
The scrapling-fetch skill SHALL expose `openalex.work(doi_or_id: str) -> OpenAlexWork`,
`openalex.references(id_: str) -> List[PaperRef]`, and
`openalex.citations(id_: str) -> List[PaperRef]`.

#### Scenario: Work lookup returns an OpenAlexWork object
- GIVEN a valid OpenAlex ID or DOI
- WHEN `openalex.work` is called
- THEN an `OpenAlexWork` dataclass is returned with a non-empty title

#### Scenario: References returns a list of PaperRef
- GIVEN a valid OpenAlex work ID
- WHEN `openalex.references` is called
- THEN a list of `PaperRef` dataclasses is returned

---

### Requirement: Semantic Scholar Fallback Adapter
The scrapling-fetch skill SHALL expose
`semantic_scholar.references(id_or_url: str) -> List[PaperRef]` and
`semantic_scholar.citations(id_or_url: str) -> List[PaperRef]` as a fallback
for OpenAlex. Pagination SHALL be handled internally and the adapter SHALL
return the union of all pages.

#### Scenario: Paginated results are fully collected
- GIVEN a paper with references spanning multiple Semantic Scholar API pages
- WHEN `semantic_scholar.references` is called
- THEN the adapter handles pagination internally and returns the complete union

---

### Requirement: DOI Resolver Adapter
The scrapling-fetch skill SHALL expose
`doi.resolve(doi: str) -> ResolvedDoi` returning a dataclass with fields:
final_url, optional publisher, optional free_pdf_url.

#### Scenario: Known DOI resolves to a final URL
- GIVEN a valid DOI
- WHEN `doi.resolve` is called
- THEN `ResolvedDoi.final_url` is a non-empty string

---

### Requirement: PDF Download with Memory Safety
The scrapling-fetch skill SHALL expose
`download_pdf(url: str, dest: Path) -> DownloadResult` returning a dataclass
with fields: path, sha256, bytes, content_type. The response SHALL be
streamed to disk so that peak process memory growth stays below 50 MB
regardless of file size.

#### Scenario: PDF is streamed to disk without memory spike
- GIVEN a remote PDF of 200 MB
- WHEN `download_pdf` is called
- THEN peak process memory growth stays below 50 MB and the file is written to `dest`

#### Scenario: Non-PDF content type raises NotAPdf and cleans up
- GIVEN a URL that serves a non-PDF Content-Type
- WHEN `download_pdf` is called
- THEN `NotAPdf` is raised and any partial file at `dest` is deleted

---

### Requirement: Adapter Isolation
The scrapling-fetch skill SHALL isolate each adapter (arxiv.py, openalex.py,
semantic_scholar.py, doi.py) so that a parse failure or site-layout change
in one adapter SHALL not block use of the others.

#### Scenario: One adapter failure does not disable siblings
- GIVEN the openalex adapter raises a parse error
- WHEN `semantic_scholar.citations` is called in the same session
- THEN the Semantic Scholar call completes successfully

---

### Requirement: No Direct Network Imports in Suite Skills
The suite's CI lint SHALL fail the build if any skill other than scrapling-fetch
imports requests, httpx, urllib3, aiohttp, or playwright at runtime.

#### Scenario: CI catches banned import in non-scrapling skill
- GIVEN a pull request that adds `import httpx` to the book-knowledge skill
- WHEN the CI lint job runs
- THEN the build fails with a diagnostic identifying the offending import

---

### Requirement: Hermetic Fixture Replay Mode
The scrapling-fetch skill SHALL ship with a recorded-fixture replay mode so
that `pytest -m "not live"` runs hermetically. A separate `pytest -m live`
suite SHALL exist to catch site-layout drift and SHALL run nightly, not on
every commit.

#### Scenario: Offline test suite passes without network
- GIVEN network access is blocked
- WHEN `pytest -m "not live"` is executed
- THEN all tests pass using fixture cassettes

#### Scenario: Live suite catches site-layout drift nightly
- GIVEN the nightly CI schedule triggers `pytest -m live`
- WHEN a source site changes its HTML layout
- THEN the live test for that adapter fails, surfacing the drift
