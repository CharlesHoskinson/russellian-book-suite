# Design: tier6-failure-mode-tests

## Why these four

Both deep-research reports
(`~/OneDrive/Desktop/Neurosymbolic Theory Induction
Framework.txt`,
`~/OneDrive/Desktop/deep-research-report.md`) catalogue
LLM-symbolic-loop failure modes. The design spec
(`docs/specs/2026-05-19-tier6-theory-induction-design.md`
§"Test plan — Layer C") narrowed to the top four:

1. **False-Correction Loop** — the LLM proposer is sensitive
   to its own error trace; a spurious validator error
   message can make it "fix" a candidate that was already
   correct. Mitigation: the proposer must be idempotent on
   the same candidate input regardless of accompanying
   error noise.
2. **Outcome-Driven Constraint Violation** — the LLM
   maximises coverage by emitting a tautology (e.g., `(or
   true any-other-thing)`). Mitigation: the validator must
   detect and reject trivial tautologies BEFORE counting
   support.
3. **Proof-Level Confabulation** — the LLM emits a rule
   that references its own defect id (a circular
   definition that lets the "proof" point at itself).
   Mitigation: the grammar enforcer must reject
   self-references in the `:assert` AST.
4. **Memorization-vs-Induction** — a candidate that fits
   the training corpus perfectly but fails on the
   document-held-out fold has memorised, not induced.
   Mitigation: the 5-fold document-held-out validation
   must reject any candidate whose held-out sat-rate falls
   below a threshold (`0.5`).

Each mitigation lives in Phase V (grammar), Phase W
(orchestrator), or Phase X (validation); this change tests
that the mitigations are wired and fire.

## Test 1 — False-Correction Loop

**Fixture:** A syntactically-valid candidate at
`tests/fixtures/failure_modes/valid_candidate.edn`. A
spurious "error" string at
`tests/fixtures/failure_modes/spurious_error.txt`.

**Test:**

```python
def test_false_correction_loop_rejected(stub_proposer):
    valid = read_edn("tests/fixtures/failure_modes/valid_candidate.edn")
    spurious = "ERROR: this candidate failed the cosmic ray check"

    # Same proposer prompt + valid candidate, called twice:
    # once with spurious error, once without.
    out_with_error = stub_proposer.propose_repair(valid, error=spurious)
    out_clean = stub_proposer.propose_repair(valid, error=None)

    # Proposer must NOT mutate the candidate on a spurious error.
    assert out_with_error == out_clean
    assert out_with_error == valid
```

**Mitigation asserted:** The proposer is idempotent when
the candidate is already grammar-clean; repair calls only
trigger on a real grammar or validation failure flagged by
the framework itself, not by free-form error text.

## Test 2 — Outcome-Driven Constraint Violation

**Fixture:** A trivially-true candidate at
`tests/fixtures/failure_modes/tautology_candidate.edn`:

```edn
(defconstraint :induced/trivial
  :scope :subject
  :backend :z3
  :assert (or true (= (:r0 ?d) (:r0 ?d))))
```

**Test:**

```python
def test_outcome_driven_constraint_violation_rejected(validator):
    candidate = read_edn("tests/fixtures/failure_modes/tautology_candidate.edn")
    result = validator.validate(candidate, atomspace=fixture_atomspace)
    assert result.rejected is True
    assert result.reason == ":trivial-tautology"
```

**Mitigation asserted:** The validator detects pure-`true`
disjuncts and identity equalities BEFORE counting support;
the rejection reason is the structured tag
`:trivial-tautology`.

## Test 3 — Proof-Level Confabulation

**Fixture:** A self-referencing candidate at
`tests/fixtures/failure_modes/circular_candidate.edn`:

```edn
(defconstraint :induced/self-ref
  :scope :subject
  :backend :z3
  :assert (= (:defect-id :D-induced-self-ref) :D-induced-self-ref)
  :on-unsat {:defect :D-induced-self-ref ...})
```

**Test:**

```python
def test_proof_level_confabulation_rejected(grammar_enforcer):
    candidate = read_edn("tests/fixtures/failure_modes/circular_candidate.edn")
    result = grammar_enforcer.grammar_conforming(candidate, schema=fixture_schema)
    assert result.ok is False
    assert result.tag == ":grammar-fail/circular-definition"
```

**Mitigation asserted:** The grammar enforcer walks the
`:assert` AST, detects a node whose value matches the
rule's own `:on-unsat` defect id, and rejects the candidate
with the `:circular-definition` tag.

## Test 4 — Memorization-vs-Induction

**Fixture:** A "fits training, fails held-out" candidate at
`tests/fixtures/failure_modes/memorized_candidate.edn`,
plus a 5-fold split fixture under
`tests/fixtures/failure_modes/holdout_folds/` (10 documents
across 5 folds).

**Test:**

```python
def test_memorization_vs_induction_rejected(orchestrator):
    candidate = read_edn("tests/fixtures/failure_modes/memorized_candidate.edn")
    folds = load_folds("tests/fixtures/failure_modes/holdout_folds/")
    result = orchestrator.validate_with_holdout(candidate, folds)

    # Held-out sat-rate is fixed in the fixture to < 0.5 on ≥1 fold.
    assert result.rejected is True
    assert result.reason == ":memorization"
    assert result.failing_folds  # at least one held-out fold below threshold
```

**Mitigation asserted:** The orchestrator runs the candidate
across all 5 folds, computes per-fold sat-rate, and rejects
when ≥1 fold's sat-rate falls below `0.5`. The rejection
reason is `:memorization`.

## File layout

```
skills/neurosym-forge/tests/
  test_failure_modes.py
  fixtures/failure_modes/
    valid_candidate.edn
    spurious_error.txt
    tautology_candidate.edn
    circular_candidate.edn
    memorized_candidate.edn
    holdout_folds/
      fold_0.jsonl
      fold_1.jsonl
      fold_2.jsonl
      fold_3.jsonl
      fold_4.jsonl
```

The four test names each carry the failure-mode label so
`pytest -k failure_mode` discovers all four uniformly. The
file name `test_failure_modes.py` is searchable by ripgrep
when a future tier wants to add a fifth pattern.

## Cost discipline

Each test uses a stub provider (no real LLM calls), a
fixture atomspace (no Cozo / Z3 invocation beyond what the
mitigation itself requires), and bounded fold counts. The
`pytest --durations=10` budget of ≤5 seconds per test is
the regression boundary; a regression that makes any test
slower than 5 seconds indicates a stub backend has fallen
back to a real provider or a fold-count default has changed
silently.

## What this change does NOT cover

The four failure modes above are the user-chosen top-4
subset. Five additional patterns from the deep-research
reports remain out-of-scope for Tier 6:

- LLM Hallucination of nonexistent predicate names (caught
  upstream by the grammar enforcer's
  `:grammar-fail/unknown-predicate` per REQ-INDUCE-042 —
  no additional test needed).
- Domain-prior leakage from training data (open research;
  no mechanical mitigation in Tier 6).
- Reward hacking through tolerance widening (mitigated by
  Phase X's bounded SMT search; opt-in regression test
  deferred).
- Distributional shift between corpora (deferred to Tier 7's
  promote-up logic).
- Provenance falsification (covered by Phase Y's
  round-trip discipline; no LLM-loop regression needed).

These are noted here so a future tier can reach for them
without re-discovering the catalogue.
