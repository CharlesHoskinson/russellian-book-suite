# Halmos QA Swarm — Design

**Goal:** Review the `halmos` skill across four dimensions with parallel QA agents, adversarially verify every gating finding before acting, apply TDD fixes for the survivors, and confirm the result by re-running the existing test suites plus halmos end-to-end on the agentic-civ book.

**Status:** approved 2026-06-02.

## Scope

Target of review: `skills/halmos/` — `scripts/{concept_ledger,build_linkage,dispatch_halmos_review,aggregate_halmos,conductor}.py`, `skill_api.py`, `references/{halmos-doctrine.md,seed-concepts.txt}`, `SKILL.md`, `README.md`, `tests/*`, plus the integration touch-point `skills/book-compose/scripts/chapter_contract_check.py` (`_read_halmos_critical` + the `halmos_critical_count` gate) and its `tests/test_halmos_gate.py`. The design spec and implementation plan under `docs/superpowers/{specs,plans}/2026-06-01-halmos-skill*.md` are inputs for the fidelity reviewer.

Out of scope: changes to other skills, the book content, or the gate's semantics beyond what a verified finding requires.

## Orchestration

A single persisted Workflow script, `qa-halmos-review`, runs five phases. Reviewers are read-only and need no worktree. Fixers run in worktree isolation. The script does not emit a "clean" top-line verdict unless the phase-5 gate is green.

```
Phase 1 REVIEW   4 reviewers (parallel, read-only)
Phase 2 VERIFY   skeptic per critical/important finding (refute-by-default), pipelined
Phase 3 SYNTH    deterministic dedup + severity bucket -> review report (.md)
Phase 4 FIX      one implementer per file-disjoint cluster, worktree, TDD
Phase 5 GATE     re-run pytest + halmos-on-book; RED blocks the clean verdict
```

Phases 1-2 are a `pipeline`: each finding enters verification as soon as its reviewer returns, so verification of one dimension overlaps review of another. Phase 3 is a barrier (dedup needs all survivors at once). Phase 4 runs disjoint clusters under `parallel` with `isolation: "worktree"`. Phase 5 is a single gate agent.

## Components

### 1. Reviewer agents (4)

Each agent receives a focused brief and the exact in-scope file list (kept disjoint so contexts stay small) and returns a schema-validated `FINDINGS` object.

- **Code correctness** — `scripts/*.py`. Watch: `_chapter_n` parsing (off-by-one, non-`ch-NN` ids), `_norm`/`_slug` collisions, `rollup._key` dedup fallback, `harvest_title_case` regex and `_ARTICLES` stripping, the `_read_halmos_critical` mtime/999 sentinel, error handling on missing or malformed files.
- **Doctrine & efficacy** — `references/halmos-doctrine.md`, `seed-concepts.txt`, and the two known limitations: footnote-title noise in concept harvesting (e.g. "Safety Gridworlds", "Existential Risk"), and `introduced_in = earliest` marking ch-01 for devices ch-1 merely previews. Judge doctrine fidelity to Halmos's spiral exposition, check completeness/severity calibration of the seven checks, and assess seam-overlap stopword tuning and false clean/broken risk.
- **Test rigor & coverage** — `tests/*.py` + `book-compose/tests/test_halmos_gate.py`. Happy-path-only tests, missing regressions, brittle assertions, untested branches, whether the gate sentinel is actually exercised.
- **Fidelity, docs & integration** — built skill vs. spec+plan (were the two plan defects — Title-Case article capture, the impossible deterministic forward-reference check — fully and correctly resolved?); SKILL.md/README accuracy and AI-slop; `chapter_contract_check` gate wiring; `skill_api` surface; sibling-skill load path.

```
FINDINGS = {
  dimension: string,
  summary: string,
  findings: [{
    id: string,                 # stable within the dimension, e.g. "code-3"
    title: string,
    severity: "critical"|"important"|"minor",
    location: string,           # "file:line" or "file"
    claim: string,              # what is wrong
    evidence: string,           # why, citing the code/text
    suggested_fix: string
  }]
}
```

### 2. Skeptic verifier

One per critical/important finding. Reads the cited region and tries to refute the claim; defaults to `refuted` when uncertain. Minor findings skip verification (cheap, non-gating) and pass through to the report flagged as unverified.

```
VERDICT = {
  finding_id: string,
  verdict: "real"|"partial"|"refuted",
  reasoning: string,
  corrected_severity: "critical"|"important"|"minor"
}
```

### 3. Synthesis

Deterministic: drop `refuted`; keep `real`/`partial`; dedup by `(file, line, check/title)`; bucket by corrected severity. Write `docs/qa/2026-06-02-halmos-qa-review.md` containing only findings and their dispositions, plus a refuted-findings appendix (what was raised, why dismissed). No review-process meta (reviewer counts, panel existence) and no counting flourishes.

### 4. Fix executor

Verified survivors are partitioned into file-disjoint clusters. One implementer per cluster, each in its own worktree, follows TDD: extend or author a failing test that captures the finding, then fix to green. Returns `{cluster, status, commit, test_result}`. A cluster that cannot reach green leaves its findings marked **unresolved** in the report with the failing output — never silently dropped. If all clusters land in one file, there is one cluster and no parallelism, which is acceptable.

### 5. Re-verify gate

A single agent runs, in the suite venv(s):
- `pytest` for `skills/halmos/tests` and `skills/book-compose/tests/test_halmos_gate.py`;
- the halmos conductor on the agentic-civ book — deterministic layer over all 15 chapters, plus the ch-13 agent path — confirming `halmos_critical_count == 0` and clean seams hold.

The report's top-line verdict is RED unless both are green. If the Doctrine & efficacy findings were all refuted, the report states that re-verify confirms only "gates still pass," not "limitations fixed."

## Error handling & honesty rules

- Refuted findings: logged in the appendix, not acted on.
- Fixer failure: finding stays open with failing test output.
- Gate failure: no "clean" claim; the report leads with what is still broken.
- No counting flourishes, no reviewer-process meta in the deliverable.
- Commits: sole attribution to Charles Hoskinson; terse messages; no AI attribution.

## Testing

The workflow harness is a one-off and is not unit-tested. Its correctness rests on schema-validated agent outputs and the phase-5 gate (the existing pytest suites + the book re-run). Every code fix the swarm applies is TDD'd by its implementer.

## Outputs

- Review report: `docs/qa/2026-06-02-halmos-qa-review.md`
- Fix commits on a dedicated branch/worktree in `russellian-book-suite`
- This spec; the implementation plan at `docs/superpowers/plans/2026-06-02-halmos-qa-swarm.md`
