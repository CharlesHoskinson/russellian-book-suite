# Capability delta: verifier-build — change: tier4-solver-partitioning

## ADD

### REQ-PERF-040 — Ubiquitous

The `smt::check_all` function in every verifier's `rust-verifier/src/smt.rs`
SHALL partition the atom set by `:subject` and run one Z3 `Solver`
instance per partition rather than asserting all atoms against a
single shared solver.

**Rationale:** A single shared solver couples per-subject decidability:
a hard subject's `:unknown` masks evidence on every other subject, and
the timeout fires for the whole corpus rather than the slow subject.
Per-subject partitioning bounds the blast radius and unlocks
parallelism. **Tested by:**
`verifiers/osmotic_pressure/rust-verifier/src/smt.rs::tests::two_subject_partition_isolates_unknown`
(added in I1.1)

### REQ-PERF-041 — Optional feature

WHERE the env var `VERIFIER_SOLVER_PARALLELISM` is set to a positive
integer `N > 1`, the framework SHALL dispatch the per-subject
partitions across up to `N` worker threads concurrently. WHEN the env
var is unset or set to `1`, the partitions SHALL run serially in
deterministic (BTreeMap-key) order.

**Rationale:** Serial-default keeps existing golden tests deterministic
and side-steps the Z3-rs cross-version thread-safety question;
parallelism is an opt-in knob for scaled corpora where wall-clock
matters more than determinism. **Tested by:**
`verifiers/osmotic_pressure/rust-verifier/src/smt.rs::tests::parallelism_four_subjects_bounded_by_max_not_sum`
(added in I4.2)

### REQ-PERF-042 — Ubiquitous

The per-subject verdicts produced by partitioned `check_all` SHALL be
merged into a single top-level `Verdict` by the rule: any partition
returning `:unsat` makes the top-level `:unsat` and the explanation
names the subject(s); otherwise any partition returning `:unknown`
makes the top-level `:unknown` and the explanation names the
timed-out subject(s) plus their `reason_unknown` strings; otherwise
the top-level is `:sat`. The top-level `core` SHALL be the union of
per-partition cores.

**Rationale:** Operators consume a single `Verdict` per `check_all`
invocation. The merge rule preserves the strictest evidence
(`:unsat` > `:unknown` > `:sat`) while surfacing which subject(s)
drove the verdict, which a single-solver run can't tell them.
**Tested by:**
`verifiers/osmotic_pressure/rust-verifier/src/smt.rs::tests::merge_rule_unsat_dominates_unknown_dominates_sat`
(added in I2.3)

### REQ-PERF-043 — Unwanted behaviour

IF an atom's value references more than one `:subject` (e.g., a
cross-subject constraint like `(approx= (:foo ?s1) (:bar ?s2) eps)`),
THEN the framework SHALL route that atom into a `:shared` partition
that runs serially AFTER all per-subject partitions complete; the
`:shared` partition's solver SHALL be seeded with the witnesses from
each per-subject partition so the cross-subject constraint can
actually decide.

**Rationale:** A constraint that walks two subjects cannot live in
either subject's partition without breaking the partition invariant
(per-subject locality). A serial `:shared` bucket preserves the
locality benefit for single-subject atoms while still admitting
cross-subject relations; running it last lets it consume the
per-subject witnesses. **Tested by:**
`verifiers/osmotic_pressure/rust-verifier/src/smt.rs::tests::cross_subject_constraint_routes_to_shared`
(added in I5.1)
