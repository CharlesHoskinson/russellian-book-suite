# Tasks: tier4-solver-partitioning

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase I for full
TDD steps. Task numbers correspond 1:1.

## Phase I.1 — Inline Rust unit test for partitioning

- [ ] I1.1: Add a `#[cfg(all(test, feature = "smt"))]` test in `verifiers/osmotic_pressure/rust-verifier/src/smt.rs` that builds a two-subject fixture (subject A: hard-NRA, subject B: trivial-Int) and asserts the top-level verdict is `:unknown` with subject A named in the explanation and subject B's `:sat` evidence preserved. (REQ-PERF-040, REQ-PERF-042)
- [ ] I1.2: Run the test — confirm it currently FAILS because today's `check_all` returns one verdict for the whole corpus.
- [ ] I1.3: Commit the failing test.

## Phase I.2 — Implement partitioning in osmotic_pressure

- [ ] I2.1: Add `fn collect_subjects(atom: &Atom) -> Vec<String>` to `verifiers/osmotic_pressure/rust-verifier/src/smt.rs`. (REQ-PERF-040, REQ-PERF-043)
- [ ] I2.2: Refactor `check_all` to bucket atoms by single-subject vs multi-subject (`:shared`), build one `Solver` per partition, and apply the existing per-atom assert loop inside each bucket. (REQ-PERF-040, REQ-PERF-043)
- [ ] I2.3: Implement the verdict merge rule per REQ-PERF-042. (REQ-PERF-042)
- [ ] I2.4: Re-run the I1.1 test — confirm PASS.
- [ ] I2.5: Commit.

## Phase I.3 — Mirror to bermuda

- [ ] I3.1: Apply the identical partition + merge logic to `verifiers/bermuda/rust-verifier/src/smt.rs`. (REQ-PERF-040, REQ-PERF-042, REQ-PERF-043)
- [ ] I3.2: Run bermuda's existing tests — confirm no regression (today's single-subject Bermuda corpus exercises the N=1 path).
- [ ] I3.3: Commit.

## Phase I.4 — Optional parallelism

- [ ] I4.1: Read `VERIFIER_SOLVER_PARALLELISM` (default 1) inside `check_all`; when N>1, use `std::thread::scope` to dispatch up to N workers across the per-subject partitions. (REQ-PERF-041)
- [ ] I4.2: Add a four-subject fixture test that asserts wall-clock time at parallelism=4 is bounded by `max(per-subject) + shared`, not the sum. (REQ-PERF-041)
- [ ] I4.3: Commit.

## Phase I.5 — Cross-subject `:shared` partition

- [ ] I5.1: Add a test fixture with an `(approx= (:foo ?s1) (:bar ?s2) ...)` cross-subject constraint and assert it lands in the `:shared` partition (not the per-subject ones) and runs serially AFTER the per-subject partitions. (REQ-PERF-043)
- [ ] I5.2: Verify the shared partition's solver can see the per-subject witnesses (asserts the cross-subject path actually decides, not just bypasses). (REQ-PERF-043)
- [ ] I5.3: Commit.

## Phase I.6 — Scaffold template + docs

- [ ] I6.1: Update `skills/neurosym-forge/assets/project-template/rust-verifier/src/smt.rs.tmpl` to emit the partitioned form so newly scaffolded verifiers inherit the structure. (REQ-PERF-040)
- [ ] I6.2: Add a paragraph to `docs/operations/neurosym-forge-runbook.md` describing the partitioning rule and the `VERIFIER_SOLVER_PARALLELISM` knob.
- [ ] I6.3: Commit.

## Phase I.7 — Open PR

- [ ] I7.1: Push branch `feat/tier4-solver-partitioning` and open PR.
- [ ] I7.2: Merge on green CI.
