# Change: tier6-candidate-generation

**Tier:** 6 of 7 (theory-induction tier)
**Branch:** `plan/tier6-theory-induction`
**Depends on:** Tier 5 (semantic-retrieval, cross-chapter),
Tier 6 Phase V (induction-grammar)

## Why

A single-source candidate generator is fragile. If the
generator is "just LLM", every candidate costs an LLM call
and the proposer's distribution biases the theory. If the
generator is "just Horn-body mining", the candidates cover
only what frequent-pair statistics surface; relational
structure with rare predicates is invisible. If the
generator is "just Popper-style typed search", the search
explodes before it discovers numeric patterns.

Both deep-research reports converged on a hybrid: AMIE /
AnyBURL-style Horn-body mining over the Cozo atomspace +
Popper-style typed search bounded by the schema's mode
declarations + LLM-shaped proposals on focused atom
clusters. Each source has different blind spots; the union
covers the space; deduplication and semantic ranking keep
the queue tractable.

## What

- A new `induce_theory.cljs` orchestrator (nbb-driven, per
  user choice) at
  `skills/neurosym-forge/scripts/induce_theory.cljs`.
- Three candidate sources behind a uniform interface:
  Horn-body mining (Cozo Datalog queries), Popper-style
  typed search (≤4 literals per rule), LLM proposer
  (Phase V).
- Per-source candidate cap (default 20, env-overridable via
  `NEUROSYM_INDUCTION_CANDIDATES_PER_SOURCE`).
- Deduplication by canonical S-expression form (alpha-
  equivalent rules collapse).
- Semantic-coherence ranking when Phase Q's `SemanticIndex`
  is present (mean pairwise cosine over cited atoms,
  descending).
- Persisted candidate queue at
  `work/induction/candidates.edn` with rejection-reason
  tags for post-mortem debugging.
- Optional LLM cost budget via
  `NEUROSYM_INDUCTION_BUDGET_USD` halting only the LLM
  source; Horn-body + Popper continue.

## Capabilities touched

- `candidate-generation` — ADD (new capability; the inducer's
  generation stage, distinct from the validation stage)

## Implementation notes

See `docs/plans/2026-05-19-tier6-theory-induction.md`,
Phase W.

## Acceptance

- 8 REQ-INDUCE IDs (050–057) ship in
  `specs/candidate-generation/spec.md`.
- A 30-atom toy corpus produces candidates from all three
  sources; deduplication collapses an alpha-equivalent
  pair to one entry; semantic ranking orders the survivors
  by cluster coherence.
- An empty / under-10-atom corpus skips Horn-body and emits
  a structured warning; Popper + LLM still produce
  candidates.
- The candidate queue at `work/induction/candidates.edn`
  carries rejection reasons for downstream debugging.
- Setting `NEUROSYM_INDUCTION_BUDGET_USD=0.01` halts the
  LLM source after the first call but Horn-body + Popper
  continue to completion.
