# Design: tier4-solver-partitioning

## Partitioning algorithm

The current `check_all` loops over `formulas: &[(ClaimId, Atom)]` once,
reading `:predicate`, `:subject`, `:value` from each atom and asserting
the equality against the single solver. The partitioned form runs in
two passes.

**Pass 1 — bucketing:**

```rust
use std::collections::BTreeMap;

let mut per_subject: BTreeMap<String, Vec<(ClaimId, Atom)>> = BTreeMap::new();
let mut shared: Vec<(ClaimId, Atom)> = Vec::new();

for (id, atom) in formulas {
    let subjects = collect_subjects(atom);  // walks :subject + nested refs
    match subjects.as_slice() {
        []      => continue,                // opaque / context atom
        [s]     => per_subject.entry(s.clone()).or_default().push((id.clone(), atom.clone())),
        _       => shared.push((id.clone(), atom.clone())),
    }
}
```

`collect_subjects` returns the unique set of subject keywords referenced
by an atom. For a plain expression atom that's just `{:subject ...}`.
For a cross-subject constraint like
`(approx= (:vant_hoff_i :KCl) (:vant_hoff_i :NaCl) 0.01)` it returns
`{:KCl, :NaCl}` and the atom routes to `shared`.

**Pass 2 — solve:**

For each `(subject, atoms)` in `per_subject`, construct a fresh
`Solver`, apply `Params { timeout: VERIFIER_SOLVER_TIMEOUT_MS }`, run
the existing per-atom assert loop, then call `solver.check()`. Collect
into `Vec<PerSubjectVerdict>`.

Then construct one final `Solver` for `shared`, populate from the
union of all per-subject witnesses (so cross-subject constraints can
reference the values), and `check()`.

## Parallelism

Default `VERIFIER_SOLVER_PARALLELISM = 1`: serial execution preserves
deterministic ordering for golden tests and avoids the Z3-rs thread
safety question (each `Solver` is independent; the `Context` may need
to be per-thread depending on `z3-rs` version).

For `N > 1`, use `std::thread::scope` to spawn workers up to N at a
time over the `per_subject` map. `BTreeMap` iteration gives
deterministic worker dispatch ordering even though completion order
differs run-to-run.

The `shared` partition does NOT participate in the parallel pool — it
runs strictly after all per-subject partitions complete because its
assertions reference the per-subject witnesses.

## Verdict merge rule (REQ-PERF-042)

Given `N` per-subject verdicts plus 1 shared verdict, the merge:

| any `:unsat`? | any `:unknown`? | top-level    |
|---------------|------------------|--------------|
| yes           | (don't care)     | `:unsat`     |
| no            | yes              | `:unknown`   |
| no            | no               | `:sat`       |

For `:unsat`, the top-level `core` is the union of all per-partition
cores; the explanation names the subject(s) that produced the unsat.
For `:unknown`, the explanation names the subject(s) that timed out
plus their `reason_unknown` strings.

## Why not per-predicate partitioning?

Predicates frequently share state across subjects (one predicate
defines what `:vant_hoff_i` means; multiple subjects instantiate it),
so partitioning by predicate would scatter the atoms for one subject
across many solvers, defeating the locality benefit. Subjects are the
correct unit because each subject's atoms describe one entity in the
domain — KCl, NaCl, Bermuda — and entities are mostly independent.

## Default parallelism = 1

Serial execution is the default because (a) the existing test suite
expects deterministic output and (b) Z3-rs thread safety varies by
version. Setting parallelism > 1 is opt-in via env var, identical to
the Tier 1 timeout knob.
