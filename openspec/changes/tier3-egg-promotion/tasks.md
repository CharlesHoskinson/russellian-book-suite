# Tasks: tier3-egg-promotion

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase G for
full TDD steps. Task numbers correspond 1:1.

## Phase G.1 — Language enum + smoke runner

- [ ] G1.1: Add `egg::define_language!` enum `BookLogicLang` to a new `verifiers/osmotic_pressure/rust-verifier/src/eqsat_lang.rs`. (REQ-EQSAT-040)
- [ ] G1.2: Replace `eqsat.rs` stub with a `build_egraph(terms: &[Expr], rules: &[Rewrite<BookLogicLang, ()>]) -> EGraph<...>` plus `canonicalise(expr: &Expr) -> Expr`. (REQ-EQSAT-040)
- [ ] G1.3: Failing integration test `tests/eqsat_smoke.rs` builds an EGraph from one rewrite and asserts saturation completes. Commit.

## Phase G.2 — Codegen of rules_for_egg.rs

- [ ] G2.1: Extend `codegen_axioms.py` to read `rules/booklogic/rules.edn` and emit `rust-verifier/src/rules_for_egg.rs` with one `egg::rewrite!` per `defrule`. (REQ-EQSAT-040)
- [ ] G2.2: Wire `codegen_axioms.py` to run `canonicalise` on every `defconstraint` LHS/RHS pair at codegen time; emit the post-saturation form. (REQ-EQSAT-041, REQ-EQSAT-042)
- [ ] G2.3: Regression test: asserting the same physics in two algebraically equivalent forms produces byte-identical Z3 assertions. Commit.

## Phase G.3 — `:backend :egg` constraints

- [ ] G3.1: Drop the `if backend != Keyword("z3"): continue` line in `codegen_axioms.py:139`; route `:egg`-backed constraints to a new `_emit_egg_prove_block` emitter. (REQ-EQSAT-043)
- [ ] G3.2: Add `eqsat::prove_equiv(lhs: &Expr, rhs: &Expr) -> ProofResult` returning `Proved`, `NotProved(StopReason)`, or `Disproved`. (REQ-EQSAT-043)
- [ ] G3.3: Verdict surface adds a `:egg-proofs` field listing each `:egg`-constraint and its proof result. Commit.

## Phase G.4 — Saturation budget + warnings

- [ ] G4.1: Wire `VERIFIER_EQSAT_NODE_LIMIT`, `VERIFIER_EQSAT_ITER_LIMIT`, `VERIFIER_EQSAT_TIMEOUT_MS` env reads into the `Runner` builder. (REQ-EQSAT-044)
- [ ] G4.2: On non-`Saturated` stop reasons, emit a `{:phase :eqsat :reason :budget-exceeded :rule ...}` entry to the verdict's `:warnings` list. (REQ-EQSAT-044)
- [ ] G4.3: Failing test `tests/eqsat_budget.rs` with a `?x -> (* ?x 1)` rule that asserts the budget warning fires deterministically. Commit.

## Phase G.5 — SUPPORT_MATRIX + docs

- [ ] G5.1: Update `skills/neurosym-forge/SUPPORT_MATRIX.md`: `defrule` from "stub" to "wired"; `defconstraint :backend :egg` from "DROP" to "wired"; trim the "Roadmap pointers" Tier 3 row. (REQ-EQSAT-045)
- [ ] G5.2: Update `skills/neurosym-forge/references/rewrite-rule-style.md` §3 and §4 to reflect the live status. (REQ-EQSAT-045)
- [ ] G5.3: Update `docs/booklogic-dsl-reference.md` §2.4 to remove the STUB banner. Commit.

## Phase G.6 — Bermuda parity + open PR

- [ ] G6.1: Mirror `eqsat.rs`, `eqsat_lang.rs`, and `rules_for_egg.rs` into `verifiers/bermuda/rust-verifier/src/`.
- [ ] G6.2: Add `verifiers/osmotic_pressure/rust-verifier/tests/eqsat_canonical.rs` exercising the 3-rule fixture. (REQ-EQSAT-046)
- [ ] G6.3: Push branch `feat/tier3-egg-promotion`; open PR; merge on green CI.
