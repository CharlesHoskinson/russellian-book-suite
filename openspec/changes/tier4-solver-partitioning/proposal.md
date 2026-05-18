# Change: tier4-solver-partitioning

**Tier:** 4 of 4
**Branch:** `feat/tier4-solver-partitioning`
**Depends on:** `tier1-solver-timeout`

## Why

Today `smt::check_all` constructs ONE Z3 `Solver` instance and asserts
every atom in the corpus against it. The Tier 1 timeout work
(`VERIFIER_SOLVER_TIMEOUT_MS`) put a wall-clock bound on the single
solver, but the bound is corpus-wide: a single intractable subject
poisons the verdict for the whole corpus, and the timeout fires for
the entire formula set rather than the slow subject. As verifiers
scale to larger corpora (book-knowledge with thousands of claims
across hundreds of subjects), this single-point-of-timeout becomes
the dominant failure mode.

Partitioning the atom set by `:subject` lets each subject get its own
Z3 instance. Three benefits fall out:

1. **Parallelism** — independent subjects check concurrently via
   worker threads when `VERIFIER_SOLVER_PARALLELISM > 1`.
2. **Per-subject blast radius** — a `:unknown` on subject `A` no
   longer hides `:unsat` evidence on subject `B`; the top-level
   verdict names exactly which subject(s) timed out.
3. **Smaller theories** — each per-subject formula set is typically
   single-theory (e.g., all-Int for one subject, all-Real for
   another), reducing Z3's combined-theory overhead.

## What

- Partition the atom set by `:subject` inside `smt::check_all`.
- Run one Z3 `Solver` instance per partition.
- Merge per-subject verdicts into one top-level verdict per the rule
  in REQ-PERF-042.
- Honour `VERIFIER_SOLVER_PARALLELISM` (default 1, serial) for
  concurrent execution.
- Route cross-subject constraints to a `:shared` partition that runs
  serially after the per-subject partitions complete.

## Capabilities touched

- `verifier-build` — MODIFY (adds REQ-PERF-040..043)

## Implementation notes

See `docs/plans/2026-05-18-tier234-and-usefulness.md`, Phase I.

## Acceptance

- `smt::check_all` builds N+1 solvers for N subjects + 1 shared
  partition (N=0 yields a single shared-only path).
- A synthetic two-subject fixture where subject A is hard-NRA and
  subject B is trivial-Int produces a top-level `:unknown` naming A,
  and the explanation includes B's `:sat` evidence.
- With `VERIFIER_SOLVER_PARALLELISM=4`, a four-subject fixture's
  wall-clock time is bounded by `max(per-subject)` plus the shared
  partition, not the sum.
- Cross-subject constraints (atoms whose value walks more than one
  subject) land in the `:shared` partition and serialise after the
  per-subject partitions.
