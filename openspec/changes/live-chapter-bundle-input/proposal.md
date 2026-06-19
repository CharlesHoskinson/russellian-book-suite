# Change: live-chapter-bundle-input

**Sprint:** V1 of the v0.6 "claim-first prose, live" mission
**Branch:** `plan/v0.6-live-integration` (roadmap); execution branch `feat/live-chapter-bundle-input`
**Capability:** `claim-first-drafting` (new)
**Roadmap:** `docs/specs/2026-06-18-kg-prose-live-integration-roadmap-design.md`
**Depends on:** the landed S1 `chapter-retrieval` capability. No upstream sprint.

## Why

The S1 chapter-retrieval bundle is built and tested, but the live book build never calls it: `book-compose`'s drafting path still selects a flat list of verified claims via `query_chapter_evidence.py`, and `chapter_bundle.py` (the S1 serializer) has no live caller. The writer receives a passage pile, exactly the thing the brief's strongest move was meant to remove.

V1 makes the bundle the writer's scaffold. Once the chapter-draft step consumes the `chapter-retrieval-bundle` — dominant communities, top load-bearing claims, open rebuttals, minimal span anchors, and the prompt scaffold — the generated prose becomes claim-first and citation-first on the real path, and the decisive S0 experiment (claim-first vs. flat bundle) becomes runnable on an actual chapter. V1 is the foundation the rest of v0.6 attaches to.

## What

1. The chapter-draft step obtains the `chapter-retrieval-bundle` for the chapter (via the book-knowledge projector through `sibling_skills`) instead of, or ahead of, the flat `query_chapter_evidence` list.
2. The drafting prompt is built from the bundle's prompt scaffold + payload sections (state the thesis, present load-bearing claims in order with their span anchors, caveat open rebuttals).
3. Load-bearing claims are presented claim-first and citation-first: each with its minimal span anchor, in the bundle's order.
4. The bundle's flags are respected — an unanchored load-bearing claim is not presented as assertable.
5. The bundle access stays read-only over the ledger; the drafting step writes only `chapters/`.

This is wiring, not new analysis: it reuses the landed S1 projector and serializer and routes their output into the existing draft flow, respecting the per-prompt budget (the known middle-chapter quality dip).

## Scope

- This change ships the bundle-driven drafting scaffold and the prompt construction from the bundle.
- It does **not** add the writer-assertion contract (V2), the warning surface (V3), code grounding (V5), or live eval (V6) — those attach to this scaffold in later sprints.
- It does not modify the S1 bundle projector or recompute communities/thesis structure.

## Requirements

See `specs/claim-first-drafting/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-DRAFT-001 | Ubiquitous | The chapter-draft step consumes the chapter-retrieval-bundle as the writer scaffold, not a flat claim list |
| REQ-DRAFT-002 | Event-driven | When a chapter is drafted, the drafting prompt is built from the bundle's prompt scaffold + payload sections |
| REQ-DRAFT-003 | Ubiquitous | The bundle is obtained via the book-knowledge projector through sibling_skills; the ledger stays read-only |
| REQ-DRAFT-004 | Ubiquitous | Load-bearing claims are presented claim-first and citation-first, each with its minimal span anchor, in bundle order |
| REQ-DRAFT-005 | Event-driven | When the bundle surfaces an open rebuttal in scope, the drafting prompt includes its caveat |
| REQ-DRAFT-006 | Unwanted | If the bundle flags an unanchored load-bearing claim, the drafting step does not present it as assertable |

## Out of scope

- The writer-assertion contract and sentence-level faithfulness checks (V2).
- Grounded/contradiction/confidence warnings in the scaffold (V3).
- Code↔claim grounding (V5) and live eval (V6).
- Any change to the S1 bundle projector or to community/thesis computation.
