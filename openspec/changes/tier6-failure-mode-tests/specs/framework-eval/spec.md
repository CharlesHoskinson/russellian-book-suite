# Capability delta: framework-eval — change: tier6-failure-mode-tests

Phases M, O, and the prior Tier 5 changes established the
`framework-eval` capability with REQ-EVAL-040..047 and
REQ-CORPUS-040..046 covering build-log discipline at 1× and
10× corpus scale. This change extends the same capability
with REQ-TEST-040..045: four regression tests targeting the
top documented LLM-symbolic-loop failure modes, plus the
shared test-suite plumbing that hosts them.

## ADD

### REQ-TEST-040 — Unwanted behaviour

IF an LLM proposer is fed a syntactically-valid `defconstraint`
candidate plus a spurious free-form "validation error"
message that did NOT originate from the framework's grammar
enforcer or validator, THEN the proposer SHALL NOT replace
the candidate with a different one. A test SHALL assert
that the proposer's output on input `(candidate,
error=<spurious>)` equals its output on input `(candidate,
error=None)` equals `candidate`.

**Rationale:** False-Correction Loop is the failure mode
where an LLM "fixes" already-correct code in response to
hallucinated or out-of-band error noise. The mitigation is
that the proposer only enters the repair loop on
framework-flagged failures (grammar-fail tags from Phase V
or validation-fail tags from Phase X); arbitrary error
strings must be inert. The idempotence test is the
mechanical regression boundary.
**Tested by:**
`tests/test_failure_modes.py::test_false_correction_loop_rejected`
(added in BB2.3)

### REQ-TEST-041 — Unwanted behaviour

IF a candidate's `:assert` body is a trivial tautology —
specifically a disjunction containing the literal `true`, an
identity equality of the form `(= X X)` for any term `X`, or
any other syntactically-recognisable always-true expression
— THEN the validator SHALL reject the candidate with
rejection reason `:trivial-tautology` BEFORE counting
support atoms or invoking Z3.

**Rationale:** Outcome-Driven Constraint Violation is the
failure mode where an LLM maximises coverage by emitting a
predicate that covers every atom but says nothing. The
mitigation is a syntactic pre-check that catches the
canonical tautology shapes; running it before the Z3 call
keeps the cost discipline tight (a tautology that reaches
the solver burns a solver call to learn what the syntax
already showed).
**Tested by:**
`tests/test_failure_modes.py::test_outcome_driven_constraint_violation_rejected`
(added in BB3.2)

### REQ-TEST-042 — Unwanted behaviour

IF a candidate's `:assert` AST contains a node whose value
matches the rule's own `:on-unsat` defect id (the rule
"refers to itself" through the defect identifier), THEN the
grammar enforcer SHALL reject the candidate with the tag
`:grammar-fail/circular-definition`.

**Rationale:** Proof-Level Confabulation is the failure
mode where an LLM emits a rule that references its own
defect as part of its assertion — a circular structure that
lets the rule "prove itself" without ever connecting to the
atomspace. The mitigation is an AST walk in the grammar
enforcer (Phase V) that checks for self-references; this
test asserts the walk fires on the canonical fixture.
**Tested by:**
`tests/test_failure_modes.py::test_proof_level_confabulation_rejected`
(added in BB4.2)

### REQ-TEST-043 — Unwanted behaviour

IF a candidate passes validation on the full training corpus
(per-corpus sat-rate at or near `1.0`) but fails on at
least one of the 5 document-held-out folds with that fold's
sat-rate below `0.5`, THEN the orchestrator SHALL reject
the candidate with rejection reason `:memorization`. The
rejection result SHALL identify the failing fold(s) in a
`failing_folds` field.

**Rationale:** Memorization-vs-Induction is the failure
mode where an LLM (or a candidate-generation heuristic) fits
the training corpus by recalling specific atoms rather than
inducing a relational structure that generalises. The
mitigation is the 5-fold document-held-out validation pass
(Phase X); rejecting candidates that fit training but fail
held-out is the discipline that keeps the framework from
emitting a rule it cannot defend on new evidence.
**Tested by:**
`tests/test_failure_modes.py::test_memorization_vs_induction_rejected`
(added in BB5.3)

### REQ-TEST-044 — Ubiquitous

All four failure-mode tests from REQ-TEST-040 through
REQ-TEST-043 SHALL live in the single file
`skills/neurosym-forge/tests/test_failure_modes.py`; each
test function name SHALL include the failure-mode label
(`false_correction_loop`,
`outcome_driven_constraint_violation`,
`proof_level_confabulation`, `memorization_vs_induction`)
so `pytest -k failure_mode` discovers all four. The shared
fixtures SHALL live alongside the test file under
`skills/neurosym-forge/tests/fixtures/failure_modes/`,
including a `holdout_folds/` subdirectory for the
memorization-vs-induction fold split.

**Rationale:** A single file with a single naming convention
makes the failure-mode catalogue grep-discoverable and lets
a future tier add a fifth pattern by following the existing
shape. Fixture co-location keeps the broken-candidate set
inspectable in one place — a reviewer can read every
canonical failure-mode input without traversing the wider
fixtures tree.
**Tested by:**
`tests/test_failure_modes.py::test_failure_modes_module_layout`
(added in BB1.1, BB6.2)

### REQ-TEST-045 — Optional feature

WHERE the test suite is run with `pytest --durations=10`,
each of the four failure-mode tests SHALL complete in under
5 seconds wall-clock. The tests SHALL use the stub LLM
provider (no real provider calls), fixture atomspaces (no
streamed Cozo / Z3 invocations beyond what the targeted
mitigation requires), and bounded fold counts.

**Rationale:** A regression that makes any failure-mode test
slower than 5 seconds indicates a stub backend has silently
fallen back to a real provider, a fold-count default has
changed, or a fixture has grown large enough to spill into
real solver time; the wall-clock budget catches each of
those without an explicit assertion in the test bodies. The
budget keeps the suite CI-friendly and cost-zero.
**Tested by:**
`tests/test_failure_modes.py` (timing surfaced through
`pytest --durations=10` in CI; added in BB6.1)
