# Tasks: tier3-cozo-runtime

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase H for
full TDD steps. Task numbers correspond 1:1.

## Phase H.1 — Wire kg.rs into make ci

- [x] H1.1: Verifier `lib.rs` (osmotic + bermuda) exposes a `run_queries` napi entry that calls `kg::run_queries(&query_edn)`; results feed the verdict builder. (REQ-DATALOG-040)
- [x] H1.2: Smoke test (`tests/cozo_query.rs`) asserts `kg::run_queries` surfaces every declared query and that empty result sets still appear. The full `work/query-results.edn` persistence is delegated to the caller (book-qa); the Rust side returns the in-memory shape. (REQ-DATALOG-040)
- [x] H1.3: Commit.

## Phase H.2 — :backend :cozo constraints

- [x] H2.1: `codegen_axioms.py` recognises `:backend :cozo` and routes through `_emit_cozo_block` into a sibling `pub fn cozo_constraints() -> Vec<(String, String)>` registry emitted next to `assert_axioms`. (REQ-DATALOG-041)
- [x] H2.2: Dispatch loop in `codegen_axioms.py` no longer silently `continue`s on `:cozo`; only `:egg` still drops (Tier 4 work). (REQ-DATALOG-041)
- [x] H2.3: `lib.rs::run_queries` lifts non-empty Cozo defects onto the verdict's `:cozo-defects` field and drives `:status` to `:unsat` on any defect. Commit.

## Phase H.3 — :queries verdict field + remedy binding

- [x] H3.1: `Verdict` gains `queries: Vec<QueryResult>` and `cozo_defects: Vec<QueryResult>`; `emit_verdict` serialises both. (REQ-DATALOG-042)
- [x] H3.2: `verdict_to_qa.py` (bermuda + new osmotic_pressure copy) reads `rules/remedies.edn`; for any `defremedy` whose `:when {:query :Q###}` references a defquery, binds the query's row count into the remedy's entry (`query_bound=true`). (REQ-DATALOG-043)
- [x] H3.3: Commit.

## Phase H.4 — Datalog timeout

- [x] H4.1: `kg::run_queries` reads `VERIFIER_DATALOG_TIMEOUT_MS` (default 10_000 ms) and wraps each Cozo script call in a `thread::spawn` + `mpsc::recv_timeout` gate. (REQ-DATALOG-044)
- [x] H4.2: On timeout the result entry carries `timed_out=true` and `sample=Some("<timeout>")`; the loop continues without panicking. `tests/cozo_query.rs::timeout_env_var_short_circuits_long_query` covers the path. Commit. (REQ-DATALOG-044)

## Phase H.5 — SUPPORT_MATRIX + docs + open PR

- [x] H5.1: `SUPPORT_MATRIX.md` flips `defquery` (wired-builder → wired), `defconstraint :backend :cozo` (DROP → wired), and `defremedy` (external → wired (query-bound)). The wired-builder legend entry is retired; `external` shrinks to "remedies whose :when does NOT reference a defquery". `test_support_matrix.py` adds positive assertions for the three new states. (REQ-DATALOG-045)
- [ ] H5.2: Update `docs/booklogic-dsl-reference.md` §2.6 (defquery) and §2.7 (defremedy). (out of Phase I scope; tracked separately)
- [x] H5.3: Push branch `feat/tier3-cozo-runtime`; open PR; merge on green CI.
