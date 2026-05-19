# Tasks: tier6-candidate-generation

See `docs/plans/2026-05-19-tier6-theory-induction.md` Phase W for full TDD steps. Task numbers correspond 1:1.

## Phase W.1 — Orchestrator skeleton

- [ ] W1.1: Author `skills/neurosym-forge/scripts/induce_theory.cljs` invokable via `nbb -m induce-theory <project-root>`. (REQ-INDUCE-050)
- [ ] W1.2: Define the `CandidateSource` protocol and a uniform `{:edn ... :cited-atoms [...] :origin <kw>}` candidate-map contract. (REQ-INDUCE-050, REQ-INDUCE-051)

## Phase W.2 — Horn-body source (AMIE / AnyBURL)

- [ ] W2.1: Implement Horn-body mining as a Cozo Datalog query enumerating frequent predicate-pair co-occurrences over the project atomspace. (REQ-INDUCE-051)
- [ ] W2.2: Wrap each surviving pair in a `(implies (p1 ?d) (p2 ?d))` candidate template; attach Cozo support count as `:support`. (REQ-INDUCE-051)
- [ ] W2.3: Small-corpus guard: when atomspace has <10 atoms, the Horn-body source returns `[]` and emits a `:corpus-too-small` warning naming the actual size. (REQ-INDUCE-054)

## Phase W.3 — Popper-style typed search

- [ ] W3.1: Derive mode declarations from `booklogic-schema.edn` predicate signatures. (REQ-INDUCE-051)
- [ ] W3.2: Bounded enumeration: ≤4 literals per rule; emit structural forms with ε placeholders for numeric parameters (filled by Phase X). (REQ-INDUCE-051)

## Phase W.4 — LLM source (Phase V binding)

- [ ] W4.1: For each Phase Q `SemanticIndex` cluster, invoke `LLMLiftProvider.propose_constraint(schema, cluster)`; pass output through Phase V's grammar enforcer; surviving forms enter the queue. (REQ-INDUCE-051)
- [ ] W4.2: Per-source cap of `NEUROSYM_INDUCTION_CANDIDATES_PER_SOURCE` (default 20). (REQ-INDUCE-051)

## Phase W.5 — Deduplication + ranking

- [ ] W5.1: Extend `_canonical.py` with `canonical_constraint_form(edn) -> str`; collapse alpha-equivalent candidates by canonical key; preserve origin set as `[:source-a :source-b]`. (REQ-INDUCE-052)
- [ ] W5.2: Semantic-coherence ranking via `SemanticIndex` mean pairwise cosine over cited atoms, descending; gracefully degrade to no ranking when `SemanticIndex` absent. (REQ-INDUCE-053)

## Phase W.6 — Queue persistence + budget

- [ ] W6.1: Persist the queue to `work/induction/candidates.edn` with `:status` and `:rejection-reason` fields; rejected candidates retain their canonical form for post-mortem. (REQ-INDUCE-055)
- [ ] W6.2: Honor `NEUROSYM_INDUCTION_BUDGET_USD`: read Phase P SQLite cache for per-call cost; halt the LLM source when budget is exhausted; Horn-body + Popper unaffected; log final spend to `work/induction/budget.json`. (REQ-INDUCE-056)

## Phase W.7 — Tests

- [ ] W7.1: Per-source unit tests: Horn-body over fixture atomspace; Popper-typed search over fixture schema; LLM source against Stub provider. (REQ-INDUCE-057)
- [ ] W7.2: Deduplication test: two sources produce alpha-equivalent candidates; queue carries a single entry with merged origin set. (REQ-INDUCE-057)
- [ ] W7.3: Semantic-ranking integration test: SemanticIndex present → queue ordered by descending coherence; SemanticIndex absent → unranked but stable order. (REQ-INDUCE-057)
- [ ] W7.4: Budget halt test: `NEUROSYM_INDUCTION_BUDGET_USD=0.01` cuts LLM source after first call; Horn-body + Popper complete. (REQ-INDUCE-056)

## Phase W.8 — Commit

- [ ] W8.1: Commit orchestrator + sources + dedup + persistence + tests once W1–W7 are green.
