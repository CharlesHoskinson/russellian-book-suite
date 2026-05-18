# Tasks: tier1-solver-timeout

See `docs/plans/2026-05-18-tier1-general-purpose.md` Phase B for full
TDD steps. Task numbers correspond 1:1.

## Phase B.1 — Inline Rust unit test for hard-NRA timeout

- [ ] B1.1: Add a `#[cfg(all(test, feature = "smt"))]` test in `verifiers/osmotic_pressure/rust-verifier/src/smt.rs` that constructs a hard-NRA solver state (e.g., `x^4 + y^4 = 1, x*y > 1`) and asserts the verdict is `:unknown` within 32 seconds. (REQ-VERIFIER-BUILD-040)
- [ ] B1.2: Run the test — confirm it currently HANGS or fails on no-timeout. (Use `--timeout 60` in cargo test.)
- [ ] B1.3: Commit the failing test.

## Phase B.2 — Implement the timeout in osmotic_pressure

- [ ] B2.1: Modify `verifiers/osmotic_pressure/rust-verifier/src/smt.rs` to read `VERIFIER_SOLVER_TIMEOUT_MS` env var (default 30000), call `solver.set_params(&params)` before `solver.check()`. (REQ-VERIFIER-BUILD-040, REQ-VERIFIER-BUILD-041)
- [ ] B2.2: Re-run the test — assert PASS within 32 s with `:unknown`.
- [ ] B2.3: Confirm clean + doctored unit tests still pass (no regression).
- [ ] B2.4: Commit.

## Phase B.3 — Mirror to bermuda

- [ ] B3.1: Apply the identical timeout block to `verifiers/bermuda/rust-verifier/src/smt.rs`. (REQ-VERIFIER-BUILD-040)
- [ ] B3.2: Run bermuda's existing tests — confirm no regression.
- [ ] B3.3: Commit.

## Phase B.4 — Pytest smoke harness :unknown distinguishability

- [ ] B4.1: Modify `verifiers/osmotic_pressure/tests/test_smoke.py` to raise an explicit `pytest.fail("solver returned :unknown — likely timeout or theory-incompleteness")` when status is `:unknown`, distinct from `:sat`/`:unsat` mismatches. (REQ-VERIFIER-BUILD-042)
- [ ] B4.2: Add a unit test for the `_verdict_status` helper that returns `:unknown` cleanly. (REQ-VERIFIER-BUILD-042)
- [ ] B4.3: Mirror to `verifiers/bermuda/tests/test_smoke.py`.
- [ ] B4.4: Commit.

## Phase B.5 — Scaffold template

- [ ] B5.1: Update `skills/neurosym-forge/assets/project-template/rust-verifier/src/smt.rs.tmpl` with the same timeout + env-var pattern. (REQ-VERIFIER-BUILD-043)
- [ ] B5.2: Update the scaffold-bake test to assert the baked smt.rs contains the `VERIFIER_SOLVER_TIMEOUT_MS` reference. (REQ-VERIFIER-BUILD-043)
- [ ] B5.3: Commit.

## Phase B.6 — Open PR

- [ ] B6.1: Push branch `feat/tier1-solver-timeout` and open PR.
- [ ] B6.2: Merge on green CI.
