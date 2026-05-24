---
name: book-review
description: Run multi-persona editorial reviews on a drafted chapter. Seven personas (Robert Gottlieb, Lay Reader, Domain Expert, Copyeditor, Enjoyment Reader, AI-Slop Detector, First-Time Visitor) read the chapter and return severity-tagged feedback. Critical findings soft-gate chapter release. Use when user says "review chapter X with personas", "Gottlieb pass on this chapter", "run the editorial reviews", "what would Gottlieb say about this draft", "is this chapter ready for review", "soft-gate this chapter". Do NOT use for source ingestion (use book-knowledge), prose-only style fixes (use russellian-style), chapter drafting (use book-compose), or persona reviews on prose outside the book pipeline.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
  workspace-aware: true
---

# book-review

Qualitative editorial review for chapter drafts. Dispatches up to seven persona subagents in parallel, aggregates severity-tagged findings, soft-gates release on `persona_critical_count == 0`. Panel composition is set per workspace; see `review-conductor/panels/`.

## What it owns

- Persona definitions in `personas/*.md` and conventions for new ones.
- Dispatch-packet construction, subagent prompting, review parsing.
- Aggregation into `<workspace>/chapters/drafts/<chapter_id>/persona-review.md`.
- Soft-gate semantics: critical blocks; important and minor are advisory.

## What it does NOT own

- Mechanical defect-gating on built artefacts — owned by `book-qa`.
- Sentence-grain prose discipline — owned by `russellian-style`.
- Claim verification, wiki synthesis, SHACL gates — owned by `book-knowledge`.
- Chapter drafting, release bundles, book builds — owned by `book-compose`.
- Persona rewrites. Personas comment; revisions go back through `book-compose`.

## Personas

- **Robert Gottlieb** (`personas/gottlieb.md`) — voice, cadence, AI-sloppy patterns.
- **Lay Reader** (`personas/lay-reader.md`) — accessibility, unexplained jumps.
- **Domain Expert** (`personas/domain-expert.md`) — factual accuracy against the claim ledger.
- **Copyeditor** (`personas/copyeditor.md`) — cross-chapter consistency, mechanics.
- **Enjoyment Reader** (`personas/enjoyment-reader.md`) — momentum, where the reader stops.
- **AI-Slop Detector** (`personas/ai-slop-detector.md`) — 24-pattern Wikipedia catalog of AI-writing tells.
- **First-Time Visitor** (`personas/first-time-visitor.md`) — 30-second drive-by; does the opening earn the read?

## Severity rubric

A finding is `critical` iff the persona believes the chapter must not ship as written.

- **Critical** — blocks release. Reserved for patterns each persona marks as critical. Prefer `important` if uncertain.
- **Important** — fix before publication; counted but non-gating.
- **Minor** — advisory polish.

The aggregator takes severity at face value. See `references/severity-rubric.md` for per-persona patterns and dispatch order.

## Workflow

1. **Prepare.** Verify the draft exists; load the chapter contract.
2. **Dispatch.** `scripts/review_pass.py:prepare_dispatch_packets` returns one packet per persona. Issue parallel Task-tool calls; each subagent writes to `packet.output_path`.
3. **Aggregate.** `scripts/aggregate_reviews.py:aggregate_reviews` merges reports into `persona-review.md` with counts, verdict table, substring-deduplicated findings.
4. **Soft-gate.** If `critical > 0`, surface the critical findings and stop. Otherwise surface important and minor as advisory.

## Composes with

- `book-compose` — invokes this skill in Stage 4; gates on `persona_critical_count == 0`.
- `russellian-style` — runs before review so personas see compliant prose.
- `book-knowledge` — Domain Expert reads the claim ledger and raw sources.
- `book-qa` — runs after on the built manuscript; orthogonal mechanical scope.

## Usage

- "Review chapter X with personas" — full five-persona pass.
- "Gottlieb pass on this chapter" — single-persona dispatch.
- "Is chapter X ready for review?" — preflight check.

## Tests

Five suites in `tests/`: `test_persona_loader`, `test_dispatch_review`, `test_aggregate_reviews`, `test_review_pass`, `test_sibling_skills`. Run `pytest` from the skill root. Synthetic reports in `tests/fixtures/synthetic_reviews/`.

## See also

- **`review-revise-validate`** — to take a panel's findings and drive a revision cycle through them, use the sibling `review-revise-validate` skill. It composes this skill's panel + aggregate with a gemma4:31b reviser persona, applies paragraph-level rewrites, re-runs the panel, and reports the before/after delta.
