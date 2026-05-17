# Proposal: Add Syntopical Metabook

## Intent
Build a self-curating world model that sits one layer above the existing book workspace. The metabook acquires papers from citation graphs, maintains a syntopical (cross-source) layer over the claim ledger, and projects per-chapter lenses that `book-compose` reads when drafting. This closes the gap between `book-knowledge` (which ingests sources you hand it) and `book-compose` (which drafts chapters): nothing today synthesizes across sources or maintains a structured "what does each source say about the chapter's questions" view.

## Scope
In scope:
- Acquire sources via citation-graph traversal (OpenAlex / Semantic Scholar / arxiv via Scrapling), embedding-based ranking, automated triage, booklogic-driven post-rank symbolic veto, download, handoff to book-knowledge for canonical ingest.
- Synthesize topic maps, disputed-question tables, concept-reconciliation pages, gap reports — with booklogic as the primary symbolic engine for disputed questions and concept reconciliation, and surface-form / antonym-pair heuristics as a legacy fallback.
- Project per-chapter lenses consumable by `book-compose`.
- Introduce `scrapling-fetch` as the sole network skill for the suite.
- Introduce `sibling_skills` shared package + `skill_api.py` ABI convention.
- Define the booklogic interface contract (CLJS-on-Node CLI, JSON wire format).

Out of scope:
- Drafting chapter prose (book-compose).
- Style linting (russellian-style).
- Persona review (book-review).
- Post-build mechanical QA (book-qa).
- Thesis tree maintenance (book-thesis).
- Authoring booklogic itself (separate parallel project).

## Approach
Two new Python skills + one shared package + a JSON-bridged consumer of the parallel CLJS booklogic project. The metabook never touches the network directly (only via scrapling-fetch) and never mutates the canonical workspace (only via book-knowledge). Triage thresholds and automation defaults make the pipeline unattended by design; the audit manifest is the user's review surface.
