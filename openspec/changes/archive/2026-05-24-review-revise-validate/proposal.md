# Proposal — review-revise-validate cycle

**Capability slug:** `REVISE` (full: `review-revise-validate`)
**Authors:** charles hoskinson
**Status:** Draft
**Date:** 2026-05-24

## Why

After sprint-2 + audit-fix, the russellian-book-suite has all the pieces for a closed-loop review→revise→re-validate workflow:

- `book-review --llm-backend ollama` produces panel artifacts via gemma4:31b (7 personas)
- `aggregate_reviews.py` parses those artifacts (after the YAML-frontmatter contract fix)
- `gemma4:31b` with `think=True` produces substantive, on-rubric findings

But nothing currently *uses* the panel findings to drive revision. The operator has to manually:

1. Run the panel
2. Read 7 review markdowns
3. Mentally cluster findings
4. Edit the chapter
5. Re-run the panel to check progress

This is slow, repetitive, and the manual clustering step loses convergent signal. With the new infrastructure, a single command should do the cycle and report whether revision moved the chapter forward.

## What

A new skill `review-revise-validate` that orchestrates 6 stages and produces:

- `revised-chapter.md` — the chapter after gemma4-generated paragraph rewrites
- `revisions.json` — the rewrites the reviser proposed, with rationale per change
- `cycle-report.md` — before/after panel findings counts + delta interpretation

Single-pass; no auto-iteration. Operator decides whether to re-run for another pass. Critical findings introduced by revision (regressions) are flagged loudly.

Pure-Python pieces (synthesis, apply, report) run deterministically; the only LLM steps are the two panel runs (existing) and the reviser persona dispatch (new).

## Capability slug + REQ IDs

Slug `REVISE` joins the existing slug roster:

| Slug | Capability |
|---|---|
| `EDN` | edn-boundary |
| `TRACE` | ingest-trace |
| `DSL` | booklogic-dsl |
| `BERMUDA-RULES` | bermuda-rules |
| `CLJS-ORCH` | cljs-orchestrator |
| `QA-PIPE` | qa-defect-pipeline |
| `VERIFIER-BUILD` | verifier-build |
| `OSMOTIC` | osmotic-pressure-verifier |
| **`REVISE`** | **review-revise-validate** (new) |

REQ IDs `REQ-REVISE-001` through `REQ-REVISE-008` defined in `design.md`.

## Non-goals

- Cross-chapter consistency revision (chapter is the unit)
- Voice-level prose tightening absent panel findings ("make this sentence sing" is out of scope)
- Subagent-based revision (committed to local-LLM gemma4 per prior decision; rationale in design.md §3.4)
- Auto-iteration / convergence loops (single pass; operator-driven re-runs)
- Direct edits to source manuscript (cycle always writes to a separate output file)
- New CLI flags on existing skills (composes them via subprocess; doesn't modify them)

## Success criteria

The cycle is successful when, on a real chapter with documented panel issues:

1. The reviser produces revisions that address ≥50% of the identified Critical findings
2. The re-validation pass shows Critical count strictly decreased (no Critical regressions)
3. No `original` paragraph in the reviser's output fails exact-match (no apply errors)
4. Wall-clock end-to-end (single pass) under 20 minutes on gemma4:31b warmed

These are operational; tested manually on Ch1 of `articles-of-cardano-governance.md` as the launch validation.

## Out-of-scope risks (acknowledged)

- The reviser may dilute the author's voice (gemma4:31b prose ≠ Russell's voice). Mitigation: paragraph-rewrites only (not whole-chapter), human reviews `revisions.json` before applying to source.
- Convergent signal may be over-weighted by personas with similar lenses (gottlieb + ai-slop-detector both flag mechanical patterns). Mitigation: synthesis weights by *distinct* personas, not by total finding count.
- gemma4:31b reasoning budget may push wall-clock beyond 20 min on slower hardware. Mitigation: configurable `num_predict` per stage; documented in operator guide.

## Dependencies

- `book-review` skill (existing) — provides panel + aggregation
- `llm_infra.persona_dispatch` (existing) — gemma4:31b reviser dispatch
- `llm_infra` adapter with `think=True` default (sprint-2; commit `b6d3b7a`)
- `aggregate_reviews.py` artifact-contract fix (audit-fix theme 1; commit `d611516`)

No new external dependencies. No changes to existing skills' public APIs.
