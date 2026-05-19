# Tasks: tier6-failure-mode-tests

See `docs/plans/2026-05-19-tier6-theory-induction.md` Phase
BB for full TDD steps. Task numbers correspond 1:1.

## Phase BB.1 — Test file + fixture directory skeleton

- [ ] BB1.1: Create
  `skills/neurosym-forge/tests/test_failure_modes.py` with
  module docstring referencing REQ-TEST-040..045. (REQ-TEST-044)
- [ ] BB1.2: Create
  `skills/neurosym-forge/tests/fixtures/failure_modes/`
  directory with a `holdout_folds/` subdirectory.
  (REQ-TEST-044)

## Phase BB.2 — False-Correction Loop fixture + test

- [ ] BB2.1: Author
  `tests/fixtures/failure_modes/valid_candidate.edn` — a
  syntactically-valid `defconstraint` using the fixture
  schema's predicates. (REQ-TEST-040)
- [ ] BB2.2: Author
  `tests/fixtures/failure_modes/spurious_error.txt` — a
  free-form error string the test injects as a noise input.
  (REQ-TEST-040)
- [ ] BB2.3: `test_false_correction_loop_rejected` — assert
  `propose_repair(valid, error=spurious) == propose_repair(valid, error=None) == valid`.
  (REQ-TEST-040)

## Phase BB.3 — Outcome-Driven Constraint Violation fixture + test

- [ ] BB3.1: Author
  `tests/fixtures/failure_modes/tautology_candidate.edn`
  with a `:assert (or true ...)` body. (REQ-TEST-041)
- [ ] BB3.2: `test_outcome_driven_constraint_violation_rejected`
  — assert `validator.validate(candidate).rejected is True`
  and `result.reason == ":trivial-tautology"`.
  (REQ-TEST-041)

## Phase BB.4 — Proof-Level Confabulation fixture + test

- [ ] BB4.1: Author
  `tests/fixtures/failure_modes/circular_candidate.edn`
  whose `:assert` AST references its own `:on-unsat` defect
  id. (REQ-TEST-042)
- [ ] BB4.2: `test_proof_level_confabulation_rejected` —
  assert `grammar_enforcer.grammar_conforming(...).tag ==
  ":grammar-fail/circular-definition"`. (REQ-TEST-042)

## Phase BB.5 — Memorization-vs-Induction fixture + test

- [ ] BB5.1: Author
  `tests/fixtures/failure_modes/memorized_candidate.edn` —
  a candidate that fits the training corpus but fails on at
  least one held-out fold. (REQ-TEST-043)
- [ ] BB5.2: Author
  `tests/fixtures/failure_modes/holdout_folds/fold_{0..4}.jsonl`
  — 5 fold files totalling 10 distinct documents; at least
  one fold's atom set causes the memorized candidate's
  sat-rate to drop below `0.5`. (REQ-TEST-043)
- [ ] BB5.3: `test_memorization_vs_induction_rejected` —
  assert `orchestrator.validate_with_holdout(...).reason ==
  ":memorization"` and `.failing_folds` non-empty.
  (REQ-TEST-043)

## Phase BB.6 — Wall-clock budget + pytest marker

- [ ] BB6.1: Confirm each of the four tests completes in
  under 5 seconds under `pytest --durations=10`; use the
  stub LLM provider and fixture atomspace exclusively
  (no real provider, no real Cozo / Z3 calls beyond what
  the mitigation needs). (REQ-TEST-045)
- [ ] BB6.2: Verify `pytest -k failure_mode` discovers all
  four tests (the test names carry the failure-mode label).
  (REQ-TEST-044)

## Phase BB.7 — Commit

- [ ] BB7.1: Commit `test_failure_modes.py` + the fixture
  directory once BB1-BB6 are green.
