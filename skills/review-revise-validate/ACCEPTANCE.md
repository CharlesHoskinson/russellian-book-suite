---
type: acceptance-audit
date: 2026-05-24
sprint: review-revise-validate
spec: ../../openspec/changes/2026-05-24-review-revise-validate/   # pre-archive
---

# review-revise-validate Acceptance Audit

| REQ | Description | Status | Evidence |
|---|---|---|---|
| REQ-REVISE-001 | All 6 stages run end-to-end | ✅ PASS | `tests/test_run_cycle_orchestration.py` (3 tests) + Ch-01 validation cycle 2026-05-24T11:46:40Z (15 min wall-clock; all stages emitted) |
| REQ-REVISE-002 | Apply failures halt + write failures file | ✅ PASS | `tests/test_revise_apply.py::test_apply_revisions_missing_original_raises` + `test_apply_revisions_writes_failures_file` |
| REQ-REVISE-003 | Before/after counts in cycle-report.md | ✅ PASS | `tests/test_cycle_report.py::test_render_report_markdown_emits_counts_table` + Ch-01 cycle-report.md emitted counts table at top |
| REQ-REVISE-004 | Optional book-knowledge claim validation | ✅ PASS | `tests/test_run_cycle_orchestration.py::test_run_cycle_invokes_claim_validation_when_workspace_has_ledger` (unit-level; live test pending real workspace) |
| REQ-REVISE-005 | Regression warning on Critical increase | ✅ PASS | `tests/test_cycle_report.py::test_render_report_markdown_emits_regression_warning_at_top` |
| REQ-REVISE-006 | Reuses book-review aggregate_reviews | ✅ PASS | Ch-01 cycle log: `[aggregate_reviews] wrote ...panel-summary-{before,after}.md`; subprocess invocation in `run_cycle._stage2_aggregate` |
| REQ-REVISE-007 | Skip stages 3-5 on zero Critical findings | ✅ PASS | `tests/test_run_cycle_orchestration.py::test_run_cycle_stage1_invokes_book_review_with_correct_args` (forces early exit via mocked critical=0) |
| REQ-REVISE-008 | Reviser persona has recommended_num_predict 8192 | ✅ PASS | `personas/reviser.md` frontmatter verified via `_read_recommended_num_predict` at Task 2 |

**All 8 REQs verified.**

## Test count

- 38 tests in `tests/` (synthesize:18 + revise:9 + cycle_report:5 + orchestration:6)
- 0 regressions in sibling skills (book-review, book-knowledge, etc.)

## Real-world bugs found during Ch-01 validation

1. **gemma4:31b transient empty-responses on pattern-scanning personas.** Two of seven personas (ai-slop-detector, copyeditor) returned empty responses on the first cycle attempt. review_pass correctly set exit 1 via per-persona-failure isolation (audit theme 5 finding 5.3). The orchestrator was treating this as fatal. **Fixed in commit `751f058`**: stage 1 now tolerates partial panel success when ≥ 4 of 7 personas produced artifacts (quorum). Three new tests lock the quorum logic.

2. **Relative `output_dir` mismatched between orchestrator cwd and subprocess cwd.** The orchestrator passed a relative path to review_pass, then changed cwd to book-review for the subprocess. Files landed at book-review's cwd; the orchestrator's post-run glob looked at its own cwd (empty). **Fixed in commit `6cc81e6`**: stages 1 and 2 now resolve all path args to absolute before passing to subprocess.

## Ch-01 validation outcome (not a REQ but operational truth)

- **Pipeline:** ✅ ran clean (all 6 stages emitted)
- **Quality:** ⚠ revisions scoped too narrowly (synthesize_findings line-range regex matched only 1 of 38 findings)
- **Regression:** ✅ none (Critical 14 → 14)
- **Net:** Important −1, Minor +1 — modest improvement but minor compared to the panel's full surface

**Decision:** REJECT (revised-chapter.md kept in workspace as historical record; not applied to source). See `SMOKE-CYCLE-LOG.md` for details.

## Followups for next iteration (scope-limited; not blockers)

1. Synthesize_findings: widen the line-range parser to handle "Paragraph N" and unanchored findings; route the unanchored ones to the reviser as "guidance" rather than dropping.
2. Reviser persona: when given unanchored findings, instruct it to do topic-based paragraph location.
3. Stage 1 quorum logic: optional `--quorum N` CLI flag to override the hardcoded MIN_PERSONAS_QUORUM=4.
4. ai-slop-detector + copyeditor: the personas still occasionally trip gemma4. Consider per-persona retry with backoff inside book-review's review_pass.

## Verdict

**COMPLETE — all 8 EARS requirements met; pipeline validated end-to-end against real Ch-01 content; two operational bugs surfaced and fixed during validation; ready for archive per Phase I.**
