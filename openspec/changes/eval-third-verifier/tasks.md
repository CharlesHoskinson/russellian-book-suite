# Tasks: eval-third-verifier

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase L for full
TDD steps. Task numbers correspond 1:1.

## Phase L.1 — Scaffold the third verifier

- [ ] L1.1: Scaffold `verifiers/epidemiology/` from the project-template under `skills/neurosym-forge/assets/project-template/`, copying directory structure verbatim. (REQ-EVAL-040)
- [ ] L1.2: Write `verifiers/epidemiology/rules/booklogic/sorts.edn` — declare `:disease` sort. (REQ-EVAL-040)
- [ ] L1.3: Write `verifiers/epidemiology/rules/booklogic/predicates.edn` — `:basic-reproduction-number`, `:vaccination-coverage`, `:herd-immunity-threshold` (all `:real` over `:disease`). (REQ-EVAL-040)
- [ ] L1.4: Write `verifiers/epidemiology/rules/booklogic/lifts.edn` — Python-dialect regex for "R0 = N", "coverage X%", "threshold X%" patterns. (REQ-EVAL-040, REQ-EVAL-043)

## Phase L.2 — Author constraints (build log starts here)

- [ ] L2.1: Open `docs/eval/2026-05-18-third-verifier-build-log.md`. Log every roadblock from L2.2 onward in the entry format from design.md. (REQ-EVAL-042)
- [ ] L2.2: Write `verifiers/epidemiology/rules/booklogic/constraints.edn` — `C001-coverage-above-threshold` asserting `(>= coverage threshold)`. If `>=` is not in encoder vocabulary, log the workaround and link to a candidate Tier 2 issue. (REQ-EVAL-041, REQ-EVAL-043, REQ-EVAL-046)
- [ ] L2.3: Add `C002-r0-consistency` — cross-document constraint asserting the same disease has the same R0 across all claims. If `defquery`-driven cross-claim assertion is needed, log the workaround and link to Tier 4 / Tier 3-cozo-runtime. (REQ-EVAL-041, REQ-EVAL-043, REQ-EVAL-046)

## Phase L.3 — Fixtures + green CI

- [ ] L3.1: Write 3 clean fixtures (`claims_clean_measles.jsonl`, `_polio.jsonl`, `_pertussis.jsonl`) with consistent R0/threshold/coverage. (REQ-EVAL-041, REQ-EVAL-045)
- [ ] L3.2: Write `claims_doctored_measles_below_threshold.jsonl` — coverage falls below threshold. (REQ-EVAL-041, REQ-EVAL-044)
- [ ] L3.3: Write `claims_doctored_measles_inconsistent_r0.jsonl` — two chapters quote different R0 for measles. (REQ-EVAL-041, REQ-EVAL-044)
- [ ] L3.4: Run `make ci` from `verifiers/epidemiology/`. Both doctored fixtures surface defects; all clean fixtures pass. Log any failure modes. (REQ-EVAL-041, REQ-EVAL-044, REQ-EVAL-045)
- [ ] L3.5: Add `tests/test_epidemiology_fixtures.py` asserting the above behaviour. (REQ-EVAL-044, REQ-EVAL-045)

## Phase L.4 — Usefulness report

- [ ] L4.1: Write `docs/eval/2026-05-18-framework-usefulness-report.md` — three buckets (worked first-try / required workaround / still missing) drawn from the build log. (REQ-EVAL-047)
- [ ] L4.2: For each "required workaround" entry, link the Tier 2-4 OpenSpec change that closes it (or open a new issue if none planned). (REQ-EVAL-043, REQ-EVAL-046, REQ-EVAL-047)

## Phase L.5 — Commit + PR

- [ ] L5.1: Commit `openspec(eval): third-verifier build evaluation change folder (REQ-EVAL-040..047)` (already done at openspec land).
- [ ] L5.2: Commit the verifier code, build log, and usefulness report once L1-L4 are green.
- [ ] L5.3: Push branch `eval/third-verifier` and open PR.
