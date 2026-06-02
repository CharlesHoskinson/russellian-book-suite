---
name: halmos
description: Sequential cross-chapter linkage review. Use when drafting chapter N to audit how it recalls, reuses, and builds on chapters 1..N-1 — concept linkage, handoff seams, and spiral coherence in Paul Halmos's sense. Emits halmos-review.md + halmos-verdict.json and soft-gates the chapter via halmos_critical_count == 0. Do NOT use for logical entailment (book-thesis) or persona review (review-conductor).
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
  workspace-aware: true
---

# halmos

Named for Paul Halmos, whose *How to Write Mathematics* prescribes the spiral method:
each new part recalls and refines what came before, so the reader is always prepared.
`halmos` enforces that spiral across chapters.

## Public surface (`skill_api.py`)
- `run_halmos(workspace, chapter_id, dispatcher)` — the entrypoint; chains the four below.
- `build_concept_ledger(workspace)` — `halmos/concepts.jsonl`.
- `build_linkage(workspace, chapter_id)` — `halmos/linkage/ch-NN.json` (references inventory, seam, broken-seam flag).
- `dispatch_halmos_review(workspace, chapter_id, dispatcher)` — Halmos-reviewer subagent.
- `aggregate_halmos(...)` — `chapters/drafts/<id>/{halmos-review.md, halmos-verdict.json}`.

The `dispatcher` is caller-provided: in production it issues a Task-tool call running
`references/halmos-doctrine.md`; in tests it returns a canned findings dict.

## What it checks (the Halmos doctrine)
Deterministic: `broken-seam` (the N-1 close shares no salient term with the N open).
Agent (via `references/halmos-doctrine.md`): orphan-reference, continuity-gap, missed-recall,
spiral-stall, terminology-drift, premature-definition, and a `spiral_coherence` verdict.
The deterministic layer cannot decide reference-before-introduction (a concept appearing in N
has `intro_n <= N` by construction), so the agent owns it, using the references/introduces
inventory and a per-prior-chapter introduced-concepts digest.

## Gate
Add `- halmos_critical_count == 0` to a chapter contract's `acceptance_tests`. `book-compose`'s
`chapter_contract_check` reads `chapters/drafts/<id>/halmos-verdict.json`.

## Boundaries
Reads chapters/drafts, contracts, claims, thesis. Writes `halmos/` and the two per-chapter
files only. No network.
