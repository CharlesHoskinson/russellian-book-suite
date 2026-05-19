# Design: tier5-cross-chapter

## Scope modifier surface

The `defconstraint` form gains an optional `:scope` key:

```clojure
(defconstraint X042-trial-n-agrees
  :backend :z3
  :scope   :corpus                    ; default :subject
  :assert  (forall [?t1 ?t2]
             (=> (and (= (:trial-id ?t1) (:trial-id ?t2))
                      (not= ?t1 ?t2))
                 (= (:trial-n ?t1) (:trial-n ?t2))))
  :on-unsat :D042-trial-data-disagrees)
```

When `:scope` is omitted the codegen treats it as `:scope :subject`, which
is the existing Phase J behaviour: the constraint emits into
`axioms_for_subject(solver, subject)` and runs once per subject in its
own solver. Phase R adds a third path: `:scope :corpus` emits into a
new `axioms_corpus(solver)` accessor that runs once over the union of
every subject's atoms.

## Codegen change shape

`skills/neurosym-forge/scripts/codegen_axioms.py` already emits three
generated functions per Phase J:

- `axioms_for_subject(solver, subject)` — per-subject constraints.
- `axioms_shared(solver)` — cross-subject constraints discovered by the
  Phase J `:shared` bucket walker.
- `assert_axioms(solver)` — backward-compat aggregator.

Phase R adds:

- `axioms_corpus(solver)` — every constraint whose declared `:scope`
  is `:corpus`, regardless of how many subjects its body references.

The distinction between `axioms_shared` (Phase J) and `axioms_corpus`
(Phase R) is intent vs accident: Phase J's `:shared` bucket catches
constraints that *happen* to walk more than one subject (a regression
guard). Phase R's `:corpus` scope is the author saying *deliberately*
"this constraint walks the whole corpus." The two paths are
codegen-disjoint; a constraint marked `:scope :corpus` never lands in
`axioms_shared` even if its body references multiple subjects.

## Execution order

`smt::check_all` runs in three serial stages:

1. Per-subject partitions (Phase J), possibly parallel under
   `VERIFIER_SOLVER_PARALLELISM`.
2. `:shared` partition (Phase J), serial, seeded with per-subject
   witnesses.
3. `:corpus` partition (Phase R), serial, seeded with the union of
   every subject's atoms.

The corpus partition gets one fresh `Solver` instance, the same
`VERIFIER_SOLVER_TIMEOUT_MS`, and asserts every atom in the corpus
followed by every `axioms_corpus` constraint. Because the corpus
partition is single-threaded and last, Z3 sees every binding from
every subject simultaneously — exactly what a cross-chapter trial-n
constraint needs.

## Corpus-defect explanation format

The verdict surface today has a top-level `:status`, `:core`, and
`:explanation`. Phase R adds `:corpus-defects`, a vector of maps:

```clojure
:corpus-defects
[{:constraint-id :X042-trial-n-agrees
  :defect-id     :D042-trial-data-disagrees
  :subjects      [:mizuno-2008-chap-3 :mizuno-2008-chap-7]
  :explanation   "trial-n disagrees: chap-3 says 37, chap-7 says 42"}]
```

`:subjects` lists the subjects whose atoms participated in the unsat
core. The explanation is a human-readable rendering of the conflict
suitable for `verdict_to_qa.py` to lift into a QA defect.

## Worked example — Mizuno trial in two chapters

Chapter 3 ingest produces an atom `(:trial-n :mizuno-2008-chap-3) = 37`
under subject `:mizuno-2008-chap-3`. Chapter 7 ingest produces
`(:trial-n :mizuno-2008-chap-7) = 42` under subject
`:mizuno-2008-chap-7`. Both atoms also carry a `:trial-id "mizuno-2008"`
binding.

Under Phase J alone each subject's solver `:sat`-isfies trivially.
Under Phase R the corpus solver sees both atoms, the
`X042-trial-n-agrees` constraint quantifies over all trial-id-equal
pairs, and the inequality `37 ≠ 42` triggers `:unsat`. The verdict's
`:corpus-defects` field names both subjects and the disagreement.

## Why a separate scope keyword rather than auto-detect?

Phase J's `:shared` bucket already auto-detects multi-subject
constraints. Phase R could lean on that and silently widen `:shared`
to "any constraint that references >1 subject runs over the corpus
union." But the author intent matters: a `:shared`-bucketed constraint
is a guard against accidental cross-subject coupling; a `:corpus`-scoped
constraint is an explicit cross-corpus obligation. Splitting the
surface keeps the failure mode legible — a `:shared` unsat means
"your single-subject rule leaked"; a `:corpus` unsat means "your
cross-corpus invariant broke."
