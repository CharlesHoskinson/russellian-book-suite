# Sprint 2 — codegen & induction soundness

**Date:** 2026-06-16. Follows Sprint 1 (verifier chain, landed #225/#227/#228/#229).
Centerpiece: make v0.5 quantifiers **sound** (predicate-as-uninterpreted-function).
Bundles the remediation plan's Sprint 2 (neurosym-forge) and a CI hotfix track.

**Source specs:**
- `openspec/changes/booklogic-v0.6-predicate-uf-semantics/` — centerpiece (new)
- `openspec/changes/audit-remediation-2026-06/` — H-01/H-02/T2.3 (existing)
- `docs/audits/2026-06-16-ci-followup-audit/` — CI hotfix P0-A/P0-B (new)

**Conventions:** one problem per PR; TDD (failing test cites REQ/finding ID);
never push to `main` directly; no AI attribution; verify Rust/cljs via CI, not
locally (Windows libz3 link is a known skip).

---

## Track 1 — Centerpiece: quantifier soundness (v0.6 predicate-UF)

The v0.5 quantifier encoder is structurally complete but unsound: a predicate
inside a quantifier body emits an opaque `Bool::new_const` that ignores its bound
arguments (`codegen_axioms.py:1297-1300 TODO(Tier 3)`). This track declares
Bool-returning predicates as Z3 `FuncDecl`s and applies them to the bound
constants, so quantified properties actually constrain.

Detailed TDD steps: `openspec/changes/booklogic-v0.6-predicate-uf-semantics/tasks.md`
(Phases B–H, REQ-SMT-056..061, REQ-BOOKLOGIC-054..056). Design and emission shape:
that change's `design.md`. Net new file all-Python at the codegen layer; behaviour
gated behind the predicate-UF registry, so shipped verifiers are byte-identical
(REQ-SMT-061, also closes v0.5's never-formalized REQ-SMT-055).

**Definition of done:** the soundness test (REQ-SMT-060) distinguishes an entailed
universal (`:unsat`) from a non-entailed one (`:sat`) — the case the v0.5 encoder
could not; SUPPORT_MATRIX quantifier row reads **wired**; `TODO(Tier 3)` gone.

## Track 2 — Remediation Sprint 2 (neurosym-forge): H-01, H-02, T2.3

From `openspec/changes/audit-remediation-2026-06/tasks.md`. H-02 lives in the
**same file** as Track 1 (`codegen_axioms.py`), so sequence H-02 alongside Track 1
to avoid churn.

- **T2.2 / H-02 — codegen identifier injection hardening.** Route every
  `new_const`/`from_str` arg through `_rust_string_literal`/`json.dumps`
  (`codegen_axioms.py:1019,1021,1044`); validate `constraint_id` against a strict
  regex (`forge_cli.py:233`). Failing test: an id/string with `"`/`\`/newline must
  not break out of the emitted Rust. (Track 1's `apply` path must also escape
  predicate names — fold the audit's escaping into the new emission so it lands hardened.)
- **T2.1 / H-01 — induction holdout + tautology gates into the CLJS `-main`.**
  `induce_theory.cljs:407-435` persists without the holdout-validation / tautology
  pre-check the Python orchestrator runs (`_induction_orchestrator.py:317,342`).
  Failing test: `forge induce` rejects a tautological/memorizing candidate via the
  CLI path, not just via direct Python `run()`.
- **T2.3 — bake test asserts codegen output.** `test_scaffold_bake.py:65` — after
  `make ci`, read `axioms.rs` and assert the smoke fixture's constraint id + tracker
  call landed (better: a known-unsat fixture asserting the emitted defect).

## Track 3 — CI hotfix (out-of-band, from the follow-up audit)

These are not in the 5-sprint remediation plan; the follow-up audit surfaced them
against the live repo. Both are release-blocking for a trustworthy `main`.

- **P0-A — apply the branch-protection ruleset.** Admin runs
  `bash scripts/ruleset-apply.sh`; verify `gh api .../rulesets` is non-empty/active
  and `.../rules/branches/main` lists context `ci-required`; enqueue one trivial PR
  to confirm `merge_group` fires. The `ci-required` gate is currently inert — `main`
  accepts any push. This unblocks the value of every prior hardening item.
- **P0-B — de-flake the neurosym z3 test.** `test_smt_fit.py:186` — tolerate an
  effectively-zero epsilon (`eps is None or abs(eps) < 1e-9`) or pin a deterministic
  z3 config. A flaky **required** check wedges the merge queue once P0-A is live, so
  do P0-B before/with P0-A.

## Sequence

1. **Track 3 first** (P0-B then P0-A) — protect `main` on a green, deterministic gate
   so the rest of the sprint merges through a real queue.
2. **Track 1 + H-02 together** — both touch `codegen_axioms.py`; land the escaping
   inside the new `apply` emission.
3. **H-01, T2.3** — independent neurosym work, parallelizable.
4. **Docs + golden + cargo-check** (Track 1 Phases G–H) close the sprint.

## Out of scope (next sprints)

Remediation Sprint 3 (book-pipeline correctness: H-05/H-07), Sprint 4 (robustness),
Sprint 5 (coverage + CI track: P1-A/P1-B/P1-C, P2-A/B/C). Non-Bool uninterpreted
functions, trigger patterns, and schema arg-sort inference (see v0.6 proposal
"Out of scope").
