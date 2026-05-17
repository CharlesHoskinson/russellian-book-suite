# Capability delta: cljs-orchestrator — change: booklogic-cleanup

## ADD

### REQ-CLJS-ORCH-001 — Ubiquitous

The `verifiers/bermuda/cljs-orchestrator/shadow-cljs.edn` configuration shall
declare a `:node-test` build target named `:test` with `:output-to "target/node-test.js"`
and `:ns-regexp "-test$"`, so that `npx shadow-cljs compile test` produces the
file at the path the CI job invokes.

**Rationale:** Without an explicit `:output-to`, the path the CI job runs would
be undefined; the test runner needs both the target declaration and a stable
output path.
**Tested by:** Existence check in `verifiers/bermuda/cljs-orchestrator/shadow-cljs.edn` plus the `cljs-bermuda-test` CI job that runs `npx shadow-cljs compile test && node target/node-test.js` (added in cleanup T3.1)

### REQ-CLJS-ORCH-002 — Ubiquitous

The `bermuda.unify` module shall pass `cljs.test` cases for: identity
unification (a = a → bindings = `[a a]`); and unifying two distinct ground
atoms (no bindings).

**Rationale:** Module currently has zero tests; latent regressions are
silent. The minimum gate is at least one positive + one negative case.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/unify_test.cljs` (added in cleanup T3.2)

### REQ-CLJS-ORCH-003 — Ubiquitous

The `bermuda.ir` module shall pass `cljs.test` cases for malli round-trip of
each of `Atom`, `Formula`, `Claim`, `Verdict`.

**Rationale:** The malli schemas are the public surface; a regression in any
schema breaks contracts across the pipeline.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/ir_test.cljs` (added in cleanup T3.3)

### REQ-CLJS-ORCH-004 — Ubiquitous

The `bermuda.nl-to-fol` module shall pass a `cljs.test` case for `claim->formula`
applied to a quantity-shaped claim (`{:o {:kind :quantity :value 9 :unit "count"}}`)
that produces a `Formula` matching the `ir/Formula` schema.

**Rationale:** Surfaces the latent schema-collision bug the audit flagged
(`~?pred` plus `:variable` shape vs. `:keyword` constraint).
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs::claim->formula-quantity-shape` (added in cleanup T3.4)

### REQ-CLJS-ORCH-005 — Ubiquitous

The `bermuda.phases` module shall pass `cljs.test` cases for: a valid input
passing `translate`; and an invalid input (a `Claim` missing the required
`:source` field) triggering the malli pre-contract violation.

**Rationale:** Pre/post contracts are silent unless an exception is raised.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/phases_test.cljs` (added in cleanup T3.5)

### REQ-CLJS-ORCH-006 — Ubiquitous

The `bermuda.bridge` module shall pass `cljs.test` cases for: `verify-formulas`
invoked with a stub `bermuda-verifier.node` returning a known verdict EDN
string; the returned value is the parsed EDN.

**Rationale:** The bridge does not currently load in the test runner because
the napi addon is not built. A stub permits the test path without building Rust.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/bridge_test.cljs` (added in cleanup T3.6)

### REQ-CLJS-ORCH-007 — Ubiquitous

The `bermuda.core` module shall pass `cljs.test` cases for: `main` dispatching
on each of `"translate"`, `"verify"`, `"typeset"`; and any other arg printing
usage and exiting 2.

**Rationale:** The CLI is the entry point for every CI verification.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/core_test.cljs` (added in cleanup T3.7)

### REQ-CLJS-ORCH-008 — Event-driven

When `claim->formula` receives a `Claim` whose `:p` is a keyword (the
common case), the `Formula` shall not violate the `ir/Formula` malli schema.

**Rationale:** The audit flagged this case as schema-violating today.
Fixing the rule is REQ-CLJS-ORCH-008.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs::claim->formula-keyword-pred` (added in cleanup T4.1)

### REQ-CLJS-ORCH-009 — Ubiquitous

The `.github/workflows/ci.yml` workflow shall include a job named
`cljs-bermuda-test` that on every PR runs `npx shadow-cljs compile test &&
node target/node-test.js` from `verifiers/bermuda/cljs-orchestrator/` (the
path matches the `:output-to` declared in `shadow-cljs.edn` per REQ-CLJS-ORCH-001)
and fails the PR if any test fails.

**Rationale:** Without a CI gate, the new test target is best-effort. CI
makes the gate canonical.
**Tested by:** Workflow run on the PR (added in cleanup T5.1)

## MODIFY

(none)

## REMOVE

(none)
