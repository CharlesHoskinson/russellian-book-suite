# Tasks: tier4-solver-partitioning

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase J for full
TDD steps. Task numbers track that document.

## Phase J.1 — Partition atoms by subject

- [x] J1.1: Refactor `check_all` in both `verifiers/osmotic_pressure/rust-verifier/src/smt.rs` and `verifiers/bermuda/rust-verifier/src/smt.rs` to produce `BTreeMap<String, Vec<(ClaimId, Atom)>>` keyed by subject. (REQ-PERF-040)
- [x] J1.2: Per-partition solver — fresh `Solver::new()` with the existing timeout, per-subject axioms, atom binding, `check()`. (REQ-PERF-040)
- [x] J1.3: Merge rule per REQ-PERF-042 — any unsat dominates; else any unknown dominates; else sat. Explanation names the offending subject(s).
- [x] J1.4: Codegen change in `skills/neurosym-forge/scripts/codegen_axioms.py`: emit `axioms_for_subject(solver, subject)`, `axioms_shared(solver)`, `axioms_subjects() -> &'static [&'static str]`, and keep `assert_axioms(solver)` as a backward-compat aggregator. Re-vendor lib copy to osmotic_pressure (bermuda uses the canonical script via `skills/neurosym-forge/scripts/codegen_axioms.py`).

## Phase J.2 — `VERIFIER_SOLVER_PARALLELISM` env var (REQ-PERF-041)

- [x] J2.1: Read the env var, default 1. With N>1, dispatch partitions through `rayon::ThreadPoolBuilder`.

## Phase J.3 — Cross-subject `:_shared` bucket (REQ-PERF-043)

- [x] J3.1: Codegen walks the `:assert` sexp collecting `?subject-id`/`:subject` references; constraints with >1 distinct subject land in `axioms_shared`.
- [x] J3.2: Shared bucket runs serially AFTER per-subject buckets in `check_all`.

## Phase J.4 — Cargo integration test (REQ-PERF-040..043)

- [x] J4.1: `verifiers/osmotic_pressure/rust-verifier/tests/partitioning.rs` — three-subject fixture, deliberate per-subject `:unknown`, parallel-vs-serial verdict equality. Inline `smt.rs` tests cover the unit-level merge rule, the partition-isolation contract, and the parallelism dispatch path.

## Phase J.5 — PR

- [ ] J5.1: Push `feat/tier4-solver-partitioning` and open PR-J.
- [ ] J5.2: Merge on green CI.
