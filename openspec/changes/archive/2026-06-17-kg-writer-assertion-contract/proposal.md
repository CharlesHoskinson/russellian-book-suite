# Change: kg-writer-assertion-contract

**Sprint:** S2 of the v0.5 KG-for-prose mission
**Branch:** `plan/kg-prose-roadmap` (roadmap); execution branch `feat/kg-writer-assertion-contract`
**Capability:** `attributed-generation` (new)
**Roadmap:** `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md`
**Depends on:** the current claim/source-span model. Consumes S1's `chapter-retrieval-bundle` as input but is not blocked by it. Measured by S0 (`kg-prose-eval`).

## Why

`book-compose` generates sentences ephemerally. Nothing in the ledger binds a generated sentence to the claim and span it asserts, and nothing checks that the sentence is faithful to its cited span. A reader cannot trace a published sentence back to its evidence, and the writer is never told that a sentence drifted off the span it cites.

The brief's move #2 makes every sentence claim-first and citation-first: bind it to a `claim.id` and a `source-span.id`, check that the sentence is supported by its cited span, and revise or downgrade it on failure rather than publishing it unchanged. This is the highest-evidence prose-quality win after the bundle ("Attribute First, then Generate"; FActScore; RARR; CiteEval). It governs the *output* of writing, where S1's bundle governs the *input*.

## What

1. A first-class `writer-assertion` entity, materialized per generated sentence: `sentence-text`, `asserts-claim` (≥1 `claim.id`), `cites-span` (≥1 `source-span.id`), `citation-check-status`, `revision-origin`.
2. A post-generation sentence→span faithfulness check behind a seam (a small NLI / citation-faithfulness model, stubbable via an injected `llm_call`), returning support `full` / `partial` / `none`.
3. A deterministic revise-or-downgrade loop (RARR): on failure, revise the sentence from the cited span, or downgrade it to a hedged, non-canonical form flagged `partial-support`; never publish it unchanged.
4. Atomic-fact decomposition (FActScore): a `draft-atomic-fact` relation over draft prose; each fact maps to an existing claim or to a `novel-draft-claim`. Facts without KG support trigger a revise loop against the KG (not the open web); publication of the paragraph is blocked until a `novel-draft-claim` is ingested with evidence or removed.

The check seam, the revise/downgrade policy, and the decomposition pass live in `book-compose` + `book-qa`; the `writer-assertion` and `draft-atomic-fact` schema additions are owned by `book-knowledge` (ledger ownership).

## Scope

- This change ships the `writer-assertion` entity + schema, the faithfulness-check seam, the revise/downgrade policy, and atomic-fact decomposition.
- It does **not** ship the chapter bundle input (S1) — S2 consumes the bundle but does not produce it.
- It does **not** ship grounded-acceptance labels on the asserted claims (S3) — S2 records what a sentence asserts and whether it is faithful to its span, not whether the underlying argument is accepted.
- The specific NLI / citation model choice is a design-time decision (roadmap Open Question 1), not fixed here; S2 fixes only the seam and its stub.

## Requirements

See `specs/attributed-generation/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-ATTR-001 | Ubiquitous | The `writer-assertion` binds each generated sentence to ≥1 `claim.id` and ≥1 `source-span.id` |
| REQ-ATTR-002 | Event-driven | When a sentence is generated, the system records a `writer-assertion` with its `asserts-claim` and `cites-span` |
| REQ-ATTR-003 | Event-driven | When a `writer-assertion` is checked, the sentence→span check sets `citation-check-status` to `full`/`partial`/`none` |
| REQ-ATTR-004 | Unwanted | If support is `none` or `partial`, the system revises or downgrades the sentence and SHALL NOT publish it unchanged |
| REQ-ATTR-005 | Ubiquitous | `revision-origin` records how and why a sentence was revised, giving an audit trail |
| REQ-ATTR-006 | Event-driven | When draft prose is decomposed, each atomic fact maps to an existing claim or to a `novel-draft-claim` |
| REQ-ATTR-007 | Unwanted | If a fact maps to a `novel-draft-claim`, publication of that paragraph is blocked until the claim is ingested or removed |
| REQ-ATTR-008 | Ubiquitous | The faithfulness check is offline, freezable, and deterministic given a frozen model + prompt |

## Out of scope

- The chapter bundle projector and its schema (S1).
- Grounded-acceptance labels on the asserted claims (S3) — S2 surfaces `asserts-claim` and citation status; S3 adds argument-acceptability marking.
- The concrete NLI / citation-faithfulness model selection (roadmap Open Question 1, an S2 design-time decision).
