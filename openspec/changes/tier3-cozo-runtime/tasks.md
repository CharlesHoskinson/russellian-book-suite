# Tasks: tier3-cozo-runtime

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase H for
full TDD steps. Task numbers correspond 1:1.

## Phase H.1 — Wire kg.rs into make ci

- [ ] H1.1: Verifier `main.rs` (osmotic + bermuda) calls `kg::ingest_and_summarize(&claims)` after the SMT phase; result feeds the verdict builder. (REQ-DATALOG-040)
- [ ] H1.2: Persist combined query results to `work/query-results.edn` via the existing `_edn_writer` shape. Failing test asserts the file exists post-`make ci` and contains every declared query. (REQ-DATALOG-040)
- [ ] H1.3: Commit.

## Phase H.2 — :backend :cozo constraints

- [ ] H2.1: Extend `codegen_axioms.py` to recognise `:backend :cozo` constraints and emit a `cozo_constraints.rs` module with one script per constraint. (REQ-DATALOG-041)
- [ ] H2.2: Drop the `if backend != Keyword("z3"): continue` line in `codegen_axioms.py` once egg and cozo emitters both exist (joint with tier3-egg-promotion). (REQ-DATALOG-041)
- [ ] H2.3: Merge Cozo's verdict into the unified verdict; `:status` becomes the worst-case of Z3 + Cozo. Commit.

## Phase H.3 — :queries verdict field + remedy binding

- [ ] H3.1: Verdict builder adds a `:queries [...]` field listing every query name that returned a non-empty result. (REQ-DATALOG-042)
- [ ] H3.2: For each `defremedy` whose `:when` clause references a `defquery` ID, the framework materialises `:remedy-bindings <remedy-id> :rows` = `[<query rows>]`. (REQ-DATALOG-043)
- [ ] H3.3: Commit.

## Phase H.4 — Datalog timeout

- [ ] H4.1: Wrap each Cozo script call in a `VERIFIER_DATALOG_TIMEOUT_MS` (default 10000) timeout. (REQ-DATALOG-044)
- [ ] H4.2: On timeout, surface a `{:phase :datalog :reason :datalog-timeout :query ... :elapsed-ms ...}` entry on `:warnings`. Failing test on a deliberately slow fixture. Commit. (REQ-DATALOG-044)

## Phase H.5 — SUPPORT_MATRIX + docs + open PR

- [ ] H5.1: Update `SUPPORT_MATRIX.md`: `defquery` → "wired"; `defconstraint :backend :cozo` → "wired"; `defremedy` → "wired (query-bound)" for query-bound remedies; retire the "wired-builder" legend entry. (REQ-DATALOG-045)
- [ ] H5.2: Update `docs/booklogic-dsl-reference.md` §2.6 (defquery) to remove the "consumer stub" caveat; §2.7 (defremedy) to document the query-binding shape.
- [ ] H5.3: Push branch `feat/tier3-cozo-runtime`; open PR; merge on green CI.
