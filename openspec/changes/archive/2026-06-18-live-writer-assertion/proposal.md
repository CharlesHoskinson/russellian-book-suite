# Change: live-writer-assertion

**Sprint:** V2 of the v0.6 "claim-first prose, live" mission
**Branch:** `plan/v0.6-live-integration` (roadmap); execution branch `feat/live-writer-assertion`
**Capability:** `attributed-generation` (extend)
**Roadmap:** `docs/specs/2026-06-18-kg-prose-live-integration-roadmap-design.md`
**Depends on:** V1 `live-chapter-bundle-input` — the bundle-driven drafting loop must exist to record an assertion per generated sentence. Builds on the landed S2 `attributed-generation` contract.

## Why

The S2 writer-assertion contract is built and tested, but it has no live caller: `book-compose`'s drafting loop never records a writer-assertion, never runs the sentence→span faithfulness check, and never applies the revise-or-downgrade policy on real prose. `writer_assertion.py` (the S2 contract) is exercised only by its own unit tests; not a single sentence the live build emits is bound to its claim, checked against its span, or resolved by the policy.

V2 enforces the S2 contract on the live drafting path. Every sentence the real loop emits is bound to its claim + span, run through the faithfulness check, and resolved by the revise-or-downgrade policy before it is assembled into the chapter; atomic-fact decomposition and the novel-draft-claim publication block run on real paragraphs. The faithfulness/decomposer model stays the injectable, offline, freezable seam S2 already defined — no live model joins the build.

## What

1. Every sentence the live drafting loop emits is recorded as a `writer-assertion` bound to its `asserts-claim` and `cites-span`.
2. The sentence→span faithfulness check runs on each recorded sentence and sets its `citation-check-status` to `full`, `partial`, or `none`.
3. The revise-or-downgrade policy applies before the sentence is assembled into the chapter; a sentence whose check returned `partial` or `none` is never published unchanged.
4. Atomic-fact decomposition runs on drafted paragraphs; each atomic fact maps to an existing claim or to a `novel-draft-claim`.
5. A paragraph carrying a `novel-draft-claim` is blocked from publication until the claim is ingested (via `qa/proposed-transitions.jsonl`) or the fact is removed.
6. The faithfulness and decomposer touchpoints use the injectable, offline, freezable seam S2 already defined; tests stub them and no live model runs on the build's test path.

This is wiring, not new analysis: it reuses the landed S2 contract and routes the live drafting loop's sentences through it. Ownership — book-compose records assertions under `chapters/drafts/`; novel-draft-claims route through `qa/proposed-transitions.jsonl` for book-knowledge `apply_writeback`; book-compose writes no `claims/`.

## Scope

- This change ships the live enforcement of the S2 contract on the drafting path: assertion recording, the sentence→span check, the revise-or-downgrade policy, atomic-fact decomposition, and the novel-draft-claim publication block, all on real prose.
- It does **not** ship the bundle scaffold itself (V1), the warning surface (V3), or the proof gate (V4).
- It does not introduce the concrete NLI/citation model — that stays a design-time decision; V2 uses the stub seam.

## Requirements

See `specs/attributed-generation/spec.md` (EARS). This delta ADDS REQ-ATTR-009…014 to the existing `attributed-generation` capability (the landed S2 change reached ATTR-008). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-ATTR-009 | Event-driven | When the live loop emits a sentence, it is recorded as a writer-assertion bound to its asserts-claim and cites-span |
| REQ-ATTR-010 | Event-driven | When a live-drafted sentence is recorded, the sentence→span faithfulness check runs and sets its citation-check-status |
| REQ-ATTR-011 | Unwanted | If the check returns partial or none, the revise-or-downgrade policy applies before assembly and the original is never published unchanged |
| REQ-ATTR-012 | Event-driven | When a drafted paragraph is decomposed, each atomic fact maps to an existing claim or a novel-draft-claim |
| REQ-ATTR-013 | Unwanted | If a paragraph carries a novel-draft-claim, its publication is blocked until the claim is ingested or the fact is removed |
| REQ-ATTR-014 | Ubiquitous | The live faithfulness and decomposer touchpoints use the injectable, offline, freezable seam from S2; tests stub them |

## Out of scope

- The bundle scaffold and prompt construction (V1).
- Grounded/contradiction/confidence warnings in the scaffold (V3).
- The proof-obligation gate and `qa/gated-sentences.jsonl` (V4).
- The concrete NLI/citation model behind the faithfulness/decomposer seam — design-time, still the stub seam.
- Any change to the S2 writer-assertion contract module.
