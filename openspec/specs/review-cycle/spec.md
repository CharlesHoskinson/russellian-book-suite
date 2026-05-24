# Spec delta — review-cycle capability

**Capability:** `review-cycle` (slug `REVISE`)
**Type:** ADD (new capability)
**Date:** 2026-05-24

This delta introduces a new capability `review-cycle` to the russellian-book-suite. On archive, this file is merged into a new steady-state `openspec/specs/review-cycle/spec.md`.

## Capability summary

The `review-cycle` capability orchestrates a single-pass review→revise→re-validate cycle on one chapter at a time. It composes existing skills (`book-review` for panel + aggregation; `llm_infra.persona_dispatch` for reviser dispatch) and adds three pure-Python modules (synthesize_findings, revise, cycle_report).

## EARS requirements

### REQ-REVISE-001 — Ubiquitous

The system shall run all six stages (panel-before, aggregate-before, synthesize, revise+apply, panel-after+aggregate-after, cycle-report) without operator intervention given `--chapter-id`, `--draft-path`, and an Ollama daemon serving the requested model.

### REQ-REVISE-002 — Event-driven

When the reviser's JSON output references an `original` paragraph that does not appear verbatim in the source chapter, the system shall halt with exit code 2 and write `revisions-apply-failures.json` listing the offending paragraphs.

### REQ-REVISE-003 — Ubiquitous

The system shall emit `cycle-report.md` containing before/after panel-finding counts (Critical, Important, Minor) in a comparison table at the top of the file.

### REQ-REVISE-004 — Optional feature

Where `book-knowledge` is wired into the workspace (workspace contains a `claims/` directory with a non-empty `ledger.jsonl`), the system may invoke `book-knowledge claim_validator.py` against `revised-chapter.md` as a post-apply check. The check's output is appended to `cycle-report.md` under `## Post-apply claim validation`.

### REQ-REVISE-005 — Unwanted behaviour

If the after-panel Critical count exceeds the before-panel Critical count, the system shall include a prominent `## ⚠ REGRESSION` block at the top of `cycle-report.md` (above the verdicts table) listing the new Critical findings.

### REQ-REVISE-006 — Ubiquitous

The system shall invoke `book-review aggregate_reviews.py` (the existing aggregator) for both the before and after panel runs. The system shall not implement a parallel aggregation path.

### REQ-REVISE-007 — Event-driven

When the before-panel finds zero Critical findings (sum across all personas), the system shall skip stages 3, 4, and 5 (synthesize, revise, re-validate) and emit `cycle-report.md` with a single section stating "no Critical findings; revision skipped".

### REQ-REVISE-008 — Ubiquitous

The reviser persona's frontmatter shall include `recommended_num_predict: 8192`. Lower budgets starve the JSON output (the reviser emits one JSON object per cluster, which typically requires 100-300 tokens per cluster plus reasoning overhead).

## Dependencies on other capabilities

- `qa-defect-pipeline` (`QA-PIPE`) — no direct dependency; review-cycle is a parallel workflow targeting a different review surface (panel-style editorial review vs deterministic QA gates)
- `book-review` (no capability slug; it's a skill) — review-cycle invokes its CLI for stages 1, 2, 5

## Non-requirements (explicit non-goals)

- The system shall NOT auto-iterate beyond a single pass.
- The system shall NOT edit the source manuscript file directly; revisions are always written to a separate `revised-chapter.md` in the cycle workspace.
- The system shall NOT modify any existing skill's CLI or library API.

## Test coverage requirement

Each REQ-REVISE-NNN above shall be covered by at least one test in `skills/review-revise-validate/tests/`. Test names or docstrings shall reference the REQ ID they satisfy.
