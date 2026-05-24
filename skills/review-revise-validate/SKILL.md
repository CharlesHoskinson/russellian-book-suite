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

## See also

- OpenSpec change: `openspec/changes/2026-05-24-review-revise-validate/`
- Sibling skill: `book-review` (provides panel + aggregator)
- Sibling capability: `llm_infra.persona_dispatch` (provides reviser dispatch)
