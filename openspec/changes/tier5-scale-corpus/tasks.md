# Tasks: tier5-scale-corpus

See `docs/plans/2026-05-19-tier5-scale-author.md` Phase O for full
TDD steps. Task numbers correspond 1:1.

## Phase O.1 — Scaffold the scale verifier

- [ ] O1.1: Scaffold `verifiers/adsc-clinical/` from the project-template under `skills/neurosym-forge/assets/project-template/`, copying directory structure verbatim. (REQ-CORPUS-040)
- [ ] O1.2: Write `verifiers/adsc-clinical/rules/booklogic/sorts.edn` — declare `:trial`, `:endpoint`, `:grade` sorts. (REQ-CORPUS-040)
- [ ] O1.3: Write `verifiers/adsc-clinical/rules/booklogic/predicates.edn` — at least 8 predicates spanning `:int`, `:real`, `:keyword` over the new sorts. (REQ-CORPUS-040, REQ-CORPUS-041)
- [ ] O1.4: Write `verifiers/adsc-clinical/rules/booklogic/lifts.edn` — Python-dialect regex for clinical-claim patterns ("n=X", "p<Y", "p=Y", "X mg/kg", "follow-up M months", percentages). (REQ-CORPUS-041)

## Phase O.2 — Ingest the corpus + build log opens

- [ ] O2.1: Open `docs/eval/2026-05-19-scale-corpus-build-log.md`. Every roadblock from O2.2 onward gets logged in the entry format from design.md. (REQ-CORPUS-043)
- [ ] O2.2: Author `scripts/ingest_corpus.py` to walk `~/OneDrive/Desktop/stemCells/ADSC_Complete_Report.md` (4816 lines), break into claim-sized chunks, emit a JSONL fixture stream. Confirm 1000+ claims surface after lift evaluation. Log any chunking surprises. (REQ-CORPUS-041)
- [ ] O2.3: Verify the by-predicate distribution covers at least 8 predicates with non-zero counts. Record the distribution in the build log. (REQ-CORPUS-041)

## Phase O.3 — Constraints + cross-paragraph consistency

- [ ] O3.1: Write `verifiers/adsc-clinical/rules/booklogic/constraints.edn`. Include at least one `:scope :corpus` constraint asserting the same trial referenced in two sections has consistent cohort size — exercising Phase R. Log any `:scope :corpus` gap. (REQ-CORPUS-042, REQ-CORPUS-045)
- [ ] O3.2: Build 5 clean fixtures (`claims_clean_safety_arm.jsonl`, `_efficacy_arm.jsonl`, `_dose_response.jsonl`, `_long_term_followup.jsonl`, `_combination_therapy.jsonl`). (REQ-CORPUS-042)
- [ ] O3.3: Build 3 doctored fixtures: `claims_doctored_inconsistent_cohort_size.jsonl`, `claims_doctored_pvalue_drift.jsonl`, `claims_doctored_misquoted_endpoint.jsonl`. Each targets a distinct defect class. (REQ-CORPUS-042)

## Phase O.4 — Profile + scale-eval report

- [ ] O4.1: Run `time -v make ci` from `verifiers/adsc-clinical/`. Capture wall-clock, peak RSS, and per-phase timing. (REQ-CORPUS-044, REQ-CORPUS-046)
- [ ] O4.2: For every phase whose wall-clock exceeds 5 minutes, capture `py-spy record` (Python) or `cargo flamegraph` (Rust) output under `docs/eval/profiles/`. Link from the build log. (REQ-CORPUS-044)
- [ ] O4.3: Write `docs/eval/2026-05-19-scale-eval-report.md` — six-metric table + scaling-profile section + open-gap list with tier-links. (REQ-CORPUS-046)

## Phase O.5 — Commit + tasks marked complete

- [ ] O5.1: Commit `openspec(tier5): scale-corpus change folder (REQ-CORPUS-040..046)` (done at openspec land time).
- [ ] O5.2: Commit verifier code, build log, profiles, and scale-eval report once O1-O4 are green.
- [ ] O5.3: Update `SUPPORT_MATRIX.md` if Phase O surfaces any new wired-vs-stub state.
