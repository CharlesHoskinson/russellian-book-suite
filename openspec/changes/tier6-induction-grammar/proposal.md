# Change: tier6-induction-grammar

**Tier:** 6 of 7 (theory-induction tier)
**Branch:** `plan/tier6-theory-induction`
**Depends on:** Tier 5 (llm-extractors, semantic-retrieval, cross-chapter)

## Why

The Tier 6 inducer asks an LLM to propose
BookLogic-shaped constraint candidates from atom clusters.
Without a grammar gate, an LLM is free to invent predicate
names, sorts, scopes, or operators that the BookLogic
compiler does not understand. The candidate then either (a)
crashes codegen, (b) crashes the solver, or worst, (c)
silently lifts to an OPAQUE verdict — wasting an LLM call,
a Z3 invocation, and the user's confidence.

Both deep-research reports converged on a single discipline:
**the LLM never invents the language**. It proposes inside a
fixed grammar; everything outside the grammar is rejected
BEFORE any solver runs. This change ships the enforcer that
makes that discipline mechanical.

## What

- A new `_induction_grammar.cljs` (nbb-native) exposing
  `grammar-conforming?` over a BookLogic `defconstraint`
  AST and the `booklogic-schema.edn` predicate registry.
- An LLM proposer interface reusing Phase P's
  `LLMLiftProvider` abstraction; backend selected via
  `NEUROSYM_LLM_PROVIDER` (Stub / OpenAI / Anthropic /
  Local).
- A structured rejection surface with five categories —
  non-EDN, wrong head, unknown predicate, wrong sort,
  illegal operator. Each carries a defect-class string
  consumable by the orchestrator's failure log.
- A `NEUROSYM_INDUCTION_DRY_RUN=1` switch that prints
  candidates without invoking solvers (debugging aid).
- A drift lint at `make lint` that asserts the grammar BNF
  reference stays in sync with the dispatch list in
  `codegen_axioms.py`.

## Capabilities touched

- `induction-grammar` — ADD (new capability; gate on every
  LLM-generated candidate before validation)

## Implementation notes

See `docs/plans/2026-05-19-tier6-theory-induction.md`,
Phase V.

## Acceptance

- 7 REQ-INDUCE IDs (040–046) ship in
  `specs/induction-grammar/spec.md`.
- An invalid EDN proposal is rejected by the enforcer with
  a structured error naming the failing rule; no Z3 or
  Cozo call is made on the rejected form.
- A Stub provider produces a deterministic candidate; tests
  run offline.
- `make lint` fails if a new operator is added to
  `codegen_axioms.py` without a matching entry in the
  grammar BNF reference.
