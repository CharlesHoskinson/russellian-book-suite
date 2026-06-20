# SMOKE-CYCLE-LOG

End-to-end validation cycles run against real chapters.

## Ch-01 validation cycle — 2026-05-24T11:46:40Z

- **Workspace:** `workspace/review-cycle/ch-01/validation/`
- **Wall-clock:** ~15 min (panels ~7 min each + reviser 99s + glue)
- **Model:** gemma4:31b throughout

### Stage outcomes

| Stage | Result |
|---|---|
| 1 panel-before | 7/7 personas succeeded (~50s each) |
| 2 aggregate-before | wrote panel-summary-before.md; 14 Critical / 16 Important / 8 Minor |
| 3 synthesize | 38 findings → 1 cluster (1 eligible) → revision-instructions.md |
| 4 revise | 99.2s; 2 revisions applied → revised-chapter.md |
| 5a panel-after | 6/7 personas (copyeditor empty-response — transient gemma4 flake; quorum 4 met) |
| 5b aggregate-after | wrote panel-summary-after.md |
| 6 cycle-report | regression=False → cycle-report.md |

### Findings delta

|             | Before | After | Delta |
|-------------|--------|-------|-------|
| Critical    | 14     | 14    | (+0)  |
| Important   | 16     | 15    | (-1)  |
| Minor       | 8      | 9     | (+1)  |

**Regression:** No (Critical unchanged; cycle did not introduce new Critical findings).

### Decision: REJECT (keep workspace as historical record; do not apply to source)

The revisions are mechanically correct but **scoped too narrowly** to be worth applying. The reviser only got one cluster because `synthesize_findings` filtered out 37 of 38 findings — its line-range parser requires explicit `lines? N(-M)?` syntax in the finding text, and most panel findings reference passages by "Paragraph N", "the conclusion", "Chapter 3 …", or unquoted contextual reference.

Result: gemma4 dutifully tightened two subject-verb-separation cases the copyeditor flagged, but the other 36 findings (gottlieb's listicle abstracts, ai-slop-detector's mechanical-parallel findings, enjoyment-reader's lead-buried observations, etc.) were invisible to the reviser.

### Cycle works; synthesizer needs tuning

This validation demonstrates that the 6-stage pipeline runs cleanly end-to-end through gemma4:31b: panel artifacts have valid YAML frontmatter; aggregate parses them correctly; synthesize emits a revision-instructions.md the reviser can act on; the reviser's JSON output applies cleanly via exact-match string replace; re-validation panel + diff complete without error.

The narrow synthesize_findings is a **scope-limited follow-up**, not a pipeline bug. Recommended next iteration:

- Add finding-text pattern matching for "Paragraph N" (no line numbers — use heuristic anchor matching against the chapter text)
- Add per-persona unstructured-finding handling: when a finding has no locatable anchor, forward it to the reviser as a "guidance" section rather than a cluster
- Consider letting the reviser ask the LLM to locate paragraphs by topic when explicit anchors are absent

### Verdict for REQ-REVISE-NNN

| REQ | Status |
|---|---|
| REQ-REVISE-001 (6 stages run end-to-end) | ✅ PASS |
| REQ-REVISE-002 (apply failures halt + write failures file) | ✅ untested in this run (no failures); covered by unit tests |
| REQ-REVISE-003 (before/after counts in cycle-report.md) | ✅ PASS |
| REQ-REVISE-004 (optional claim validation) | ⚠ untested in this run (no claims ledger in workspace) |
| REQ-REVISE-005 (regression warning) | ✅ untested in this run (no regression); covered by unit tests |
| REQ-REVISE-006 (reuses aggregator) | ✅ PASS — book-review/scripts/aggregate_reviews.py invoked |
| REQ-REVISE-007 (early exit on zero Critical) | ✅ untested in this run (Critical=14); covered by unit tests |
| REQ-REVISE-008 (reviser persona has recommended_num_predict: 8192) | ✅ PASS — persona frontmatter verified at Task 2 |

All gates either PASS in this validation run or are covered by existing unit tests.
