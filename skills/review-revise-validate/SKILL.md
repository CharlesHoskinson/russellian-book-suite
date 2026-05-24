---
name: review-revise-validate
description: Run a single-pass review→revise→re-validate cycle on one chapter. Dispatches the book-review panel via gemma4:31b, aggregates findings, synthesizes revision instructions, runs a gemma4 reviser persona to produce paragraph-level rewrites, applies them, re-runs the panel, and emits a before/after delta report. Use when user says "revise chapter X based on the panel", "run a revision cycle on this chapter", "what does the cycle say about ch-N". Do NOT use for cross-chapter consistency (chapter is the unit), voice-level prose tightening absent panel findings, or auto-iteration (single pass only — operator re-runs manually for further passes).
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
  workspace-aware: true
---

# review-revise-validate

Closed-loop chapter editor. Reads a chapter, runs the 7-persona panel, lets gemma4:31b propose paragraph rewrites against the findings, applies them, runs the panel again, and reports whether the chapter moved forward.

## What this owns

- `scripts/run_cycle.py` — orchestrator (6 stages)
- `scripts/synthesize_findings.py` — pure-Python clustering of panel findings into revision instructions
- `scripts/revise.py` — dispatches the reviser persona; applies the resulting paragraph rewrites
- `scripts/cycle_report.py` — diffs before/after panel summaries
- `personas/reviser.md` — the precision-editor persona
- `assets/reviser-prompt-template.md` — slot template for the reviser dispatch

## Usage

### Full cycle on a chapter

```
cd c:/governance/russellian-book-suite/skills/review-revise-validate
.venv/Scripts/python.exe -m scripts.run_cycle \
    --chapter-id ch-01 \
    --draft-path c:/governance/wiki/report/articles-of-cardano-governance.md \
    --model gemma4:31b
```

Outputs land at `workspace/review-cycle/ch-01/<ISO-timestamp>/`:
- `panel-before/persona-review-*.md` (7 files)
- `panel-summary-before.md`
- `revision-instructions.md`
- `revisions.json` + `revisions-raw-response.md`
- `revised-chapter.md`
- `panel-after/persona-review-*.md` (7 files)
- `panel-summary-after.md`
- `cycle-report.md` ← read this first

### Skip the revise step (panel + aggregate only)

```
.venv/Scripts/python.exe -m scripts.run_cycle \
    --chapter-id ch-01 \
    --draft-path PATH \
    --skip-revise
```

### Skip re-validation (revise once but don't re-panel)

```
.venv/Scripts/python.exe -m scripts.run_cycle \
    --chapter-id ch-01 \
    --draft-path PATH \
    --skip-revalidate
```

### Reading `cycle-report.md`

- **`## ⚠ REGRESSION` at the top** — revision introduced new Critical findings. Reject revisions; refine the synthesis or persona prompt.
- **`Critical | N | M | (-K)`** — K Critical findings resolved. If K > 0 and no regression block, the cycle moved the chapter forward.
- **`Net interpretation`** — one-line summary.

### Accepting revisions

The cycle never modifies the source chapter. If `cycle-report.md` looks good:

```
cp workspace/review-cycle/ch-01/<ts>/revised-chapter.md c:/governance/wiki/report/articles-of-cardano-governance.md
```

(Or apply a portion manually by reading `revisions.json` and editing selectively.)

## See also

- OpenSpec change: `openspec/changes/2026-05-24-review-revise-validate/`
- Sibling skill: `book-review` (provides panel + aggregator)
- Sibling capability: `llm_infra.persona_dispatch` (provides reviser dispatch)
