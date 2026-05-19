# Tasks: tier6-induction-grammar

See `docs/plans/2026-05-19-tier6-theory-induction.md` Phase V for full TDD steps. Task numbers correspond 1:1.

## Phase V.1 — Grammar enforcer skeleton

- [ ] V1.1: Author `skills/neurosym-forge/scripts/_induction_grammar.cljs` with a top-level `^:const` BNF block enumerating allowed heads, scopes, backends, and operators. (REQ-INDUCE-040)
- [ ] V1.2: Implement `grammar-conforming?(edn-form, schema)` returning `true` iff the form is a valid `defconstraint` referencing only schema predicates. (REQ-INDUCE-040)
- [ ] V1.3: Unit test `test_induction_grammar.py::test_valid_defconstraint_passes` against a fixture EDN file. (REQ-INDUCE-045)

## Phase V.2 — Failure surface (5 categories)

- [ ] V2.1: Return `{:tag :grammar-fail/non-edn ...}` on reader errors; `:grammar-fail/wrong-head` on non-`defconstraint`; `:grammar-fail/unknown-predicate` on out-of-schema predicates; `:grammar-fail/wrong-sort` on arg-sort mismatches; `:grammar-fail/illegal-op` on out-of-BNF operators. (REQ-INDUCE-042)
- [ ] V2.2: Unit tests `test_induction_grammar.py::test_each_failure_category_rejects_and_tags` — one test per category. (REQ-INDUCE-045)

## Phase V.3 — LLM proposer wiring

- [ ] V3.1: Extend `_llm_lift.LLMLiftProvider` with `propose_constraint(schema, atom_cluster) -> str` (single EDN form per call). Stub provider reads from `tests/fixtures/llm-responses/constraint-*.edn`. (REQ-INDUCE-041, REQ-INDUCE-043)
- [ ] V3.2: Schema-to-prompt transformation in the proposer: predicates + sorts + BNF block embedded in the system prompt. (REQ-INDUCE-041)
- [ ] V3.3: Test `test_induction_grammar.py::test_stub_provider_produces_deterministic_candidate`. (REQ-INDUCE-045)

## Phase V.4 — Dry-run switch + drift lint

- [ ] V4.1: Honor `NEUROSYM_INDUCTION_DRY_RUN=1` in the orchestrator: print candidates after grammar validation, skip solver dispatch. (REQ-INDUCE-044)
- [ ] V4.2: Drift lint `tests/test_induction_grammar_drift.py` asserting BNF block matches `codegen_axioms.OPERATOR_DISPATCH`; wire into `make lint`. (REQ-INDUCE-046)
- [ ] V4.3: Negative test: artificially add an operator to `codegen_axioms.py` test fixture; drift lint fails with the missing-operator name in the message. (REQ-INDUCE-046)

## Phase V.5 — Commit

- [ ] V5.1: Commit grammar enforcer + proposer wiring + tests + drift lint together once V1–V4 are green.
