# Change: kg-chapter-retrieval-bundles

**Sprint:** S1 of the v0.5 KG-for-prose mission
**Branch:** `plan/kg-prose-roadmap` (roadmap); execution branch `feat/kg-chapter-retrieval-bundles`
**Capability:** `chapter-retrieval` (new)
**Roadmap:** `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md`
**Depends on:** the landed `homoiconic-kg` capability. Measured by S0 (`kg-prose-eval`). No upstream sprint.

## Why

`book-compose` plans a chapter from a hand-authored contract and a flat list of verified claim ids (`query_chapter_evidence.py` returns `{chapter_id, claims}`). The writer never sees *structure*: which communities dominate the chapter, which claims are load-bearing, which counter-claims are still open, or the minimal span set it must anchor to. The graph already computes all of this — `thesis-node`, `community`, `claim-chapter`, `load-bearing`, `counter-claim`, `code-claim-link` — but the writer receives a passage pile.

The brief's strongest single move is to make the writer **claim-first and citation-first** by handing it a graph-built bundle instead of a flat list. GraphRAG's local/global retrieval is the established pattern: let communities and thesis structure plan the chapter, but let claims and source spans ground the sentences. This is a pure projector + prompt-contract change — no substrate change, no new engine — and it is the smallest path to a measurable gain in global coherence and source traceability.

## What

1. A projector materializing a `chapter-retrieval-bundle` relation per chapter from existing data, containing:
   - the dominant communities for the chapter (ranked),
   - the top load-bearing claims supporting the chapter thesis,
   - unresolved rebuttals (open counter-claims) against those claims,
   - the minimal set of source-span anchors covering the selected claims,
   - the relevant `code-claim-link` rows where the chapter describes software.
2. A serializer emitting the bundle as EDN/JSON for the writer — never a flat passage pile.
3. A prompt scaffold derived from the bundle: "state the main thesis, present the support claims in order, include a caveat on each disputed counter-claim whose rebuttal window is open."
4. The bundle is a deterministic projection (pure over a ledger snapshot), so S0 can golden it.

The projector lives in `book-knowledge` (ledger ownership) and is consumed by `book-compose`; it reuses `query_chapter_evidence.py`'s claim set and adds the community/rebuttal/anchor structure around it.

## Scope

- This change ships the projector, the bundle schema (added to `kg-schema.edn`), the serializer, and the prompt scaffold.
- It does **not** ship the writer-assertion contract or sentence→span checks (S2) — the bundle is the *input* to writing; the assertion contract governs the *output*.
- Community detection itself is unchanged; S1 consumes the existing `community` relation, it does not recompute it.
- Source-span minimization is greedy-deterministic (smallest covering set by a fixed tie-break), not an optimizer.

## Requirements

See `specs/chapter-retrieval/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-CHAP-001 | Event-driven | When the projector runs on a chapter, it materializes a `chapter-retrieval-bundle` row |
| REQ-CHAP-002 | Ubiquitous | The bundle carries dominant communities, top load-bearing claims, open rebuttals, minimal span anchors |
| REQ-CHAP-003 | Ubiquitous | The bundle is delivered as EDN/JSON, never as a flat passage pile |
| REQ-CHAP-004 | Event-driven | When a chapter has an open counter-claim in scope, the bundle surfaces it as an unresolved rebuttal |
| REQ-CHAP-005 | Ubiquitous | The projector is deterministic over a ledger snapshot (golden-able) |
| REQ-CHAP-006 | Ubiquitous | Span anchors are a minimal covering set under a fixed tie-break |
| REQ-CHAP-007 | Optional | Where the chapter describes software, the bundle includes the relevant code↔claim links |
| REQ-CHAP-008 | Unwanted | If a load-bearing claim has no source-span, the projector flags it rather than emitting an unanchored claim |

## Out of scope

- The writer-assertion contract and citation checks (S2).
- Argument-acceptability marking of the bundled claims (S3) — S1 surfaces open rebuttals as raw status; S3 adds grounded-acceptance labels.
- Recomputing community structure or thesis decomposition.
