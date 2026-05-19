# Tasks: tier5-metta-backend

See `docs/plans/2026-05-19-tier5-metta-runtime.md` Phase O for
full TDD steps. Task numbers correspond 1:1.

## Phase O.1 — Embed hyperon-experimental

- [ ] O1.1: Add `hyperon = { version = "0.2", optional = true }` to both verifiers' `Cargo.toml` gated on a new `metta` feature; pin the resolved git rev in `Cargo.lock`. (REQ-METTA-040)
- [ ] O1.2: Create `verifiers/osmotic_pressure/rust-verifier/src/metta.rs` with `pub fn run_metta(program: &str) -> Result<Vec<String>, MettaError>` and a `MettaError` enum carrying `Interpreter(String)` and `Timeout(u64)` variants. (REQ-METTA-040, REQ-METTA-043)
- [ ] O1.3: Failing integration test `tests/metta_smoke.rs` runs the 3-atom fact + rule + query fixture and asserts the printed result. Commit. (REQ-METTA-047)

## Phase O.2 — Codegen `_emit_metta_block`

- [ ] O2.1: Extend `codegen_axioms.py` dispatch loop (line ~296) with an `elif backend == Keyword("metta")` branch routing into a new `_emit_metta_block`. (REQ-METTA-041)
- [ ] O2.2: `_emit_metta_block` translates the constraint's `:assert (= (lhs ...) (rhs ...))` head into a MeTTa program string of the shape `(= (lhs $x) (rhs $x)) !(match &self ...)`. (REQ-METTA-041)
- [ ] O2.3: Emit a sibling `pub fn metta_constraints() -> Vec<(String, String)>` registry next to `cozo_constraints()`. (REQ-METTA-042)
- [ ] O2.4: `lib.rs` lifts non-empty constraints onto the verdict's `:metta-results` field and drives `:status` to `:unsat` on any `:fatal`-severity defect. Commit.

## Phase O.3 — Error + timeout surfaces

- [ ] O3.1: Wrap `Metta::new` and the `metta.run(...)` call in `std::panic::catch_unwind` to convert panics into `MettaError::Interpreter`. (REQ-METTA-043)
- [ ] O3.2: Add `VERIFIER_METTA_TIMEOUT_MS` env-var read (default 30000) and gate each `run_metta` call in a `thread::spawn` + `mpsc::recv_timeout`. (REQ-METTA-044)
- [ ] O3.3: Failing tests `tests/metta_error.rs` and `tests/metta_timeout.rs` cover the two non-defect paths. Commit. (REQ-METTA-043, REQ-METTA-044)

## Phase O.4 — SUPPORT_MATRIX + docs

- [ ] O4.1: Add `defconstraint :backend :metta` row to `skills/neurosym-forge/SUPPORT_MATRIX.md` with status `wired (alpha)`; add a new legend entry explaining the alpha qualifier. (REQ-METTA-045)
- [ ] O4.2: Update `tests/test_support_matrix.py` to assert the new row is present with the expected status. (REQ-METTA-045)
- [ ] O4.3: Update `docs/booklogic-dsl-reference.md` §2.5 to list `:metta` as a fourth backend option with the alpha caveat. Commit.

## Phase O.5 — Regression coverage + Bermuda parity

- [ ] O5.1: Add an assertion to the existing Z3 / egg / Cozo integration tests that they still pass with `--features metta` enabled. (REQ-METTA-046)
- [ ] O5.2: Mirror `metta.rs` and `metta_constraints.rs` into `verifiers/bermuda/rust-verifier/src/`. (REQ-METTA-046)
- [ ] O5.3: Push branch `plan/tier5-metta-runtime`; open PR; merge on green CI.
