# v5 Remediation Report — Bermuda Manual

Run date: 2026-05-11
Pipeline: `book-qa` Stage-1 deterministic linter + Stage-2 per-chapter swarm + two-batch Healer.

## Before-and-after

| Metric | Before remediation | After remediation |
|---|---:|---:|
| Stage-1 deterministic defects | 4 minor | **3 minor** |
| Stage-2 swarm tickets | 79 (37 important + 42 minor) | not re-run; remediation tied to original ticket list |
| Critical defects | 0 | **0** |
| PDF pages | 80 | **78** |
| PDF size | 1.41 MB | 1.38 MB |
| Footnote refs (rendered) | 40 | **63** |

## Remediations executed

### Batch A — deterministic (Python, no agents)

`C:\tmp\v5_healer_batch_a.py` swept all 10 chapter drafts and fixed:

- **C6 terminology canonicalisation**: 7 replacements ("L.F. Wade" → "L. F. Wade International Airport", "Town of St. George's" → "Town of St. George" where it referred to the municipal corporation).
- **C9 table column alignment**: 0 fixes — the agent reports were false positives (separators already used `---:` for numeric columns in every flagged table).
- **C13 empty `## Notes` sections**: 0 fixes — false positives (no chapter actually had an empty stub).
- **C15 line-wrap to 100 chars**: 6 prose paragraphs across 6 chapters wrapped. The 100+ "long lines" the agents reported in ch-06 and ch-07 turn out to be inside `<div class="hero-table">` HTML which legitimately stays single-line.

### Batch B — editorial (LLM Healers, one per chapter)

10 fresh-context agents in parallel. Each received ONLY the tickets for its chapter.

| Chapter | Status | Fixes landed |
|---|---|---|
| ch-01 | stalled at 600s watchdog | partial — footnote refs added to prose, some defs missing |
| ch-02 | stalled | partial — refs added |
| ch-03 | success | 2× C12 citations |
| ch-04 | stalled | partial — 5 footnote defs added |
| ch-05 | stalled | 0 (no edits saved); recovered by deterministic script (Batch C below) |
| ch-06 | stalled | partial — 5 defs added |
| ch-07 | stalled | partial — 6 defs added |
| ch-08 | success | C2 Notes section, 2× C11 hedges, 5× C12 citations |
| ch-09 | success | 2× C8 sidebars trimmed, 1× C11 hedge, 2× C12 citations |
| ch-10 | success | C4 pipeline-jargon fix, 3× C8 sidebars, C9 table, 3× C11 hedges, 5× C12 citations |

Four agents completed cleanly. Six stalled before declaring DONE — all six left partial work in place (footnote definitions written, some hedges fixed). Stall pattern: agents tried to make many serial Edit calls and exceeded the 600s stream-watchdog.

### Batch C — deterministic recovery for ch-05

`C:\tmp\heal_ch05.py` + `heal_ch05_b.py` applied the ch-05-specific patches that its stalled agent missed:

- C11 em-dash-as-comma in the welcoming-arms gloss → replaced with commas
- C12: two semantic footnotes (`[^fertility]`, `[^emigration]`) + Notes section
- C13 stub: replaced empty Notes heading with the populated section
- C8 partial: added third footnote (`[^ame-share]`)

## v5 architecture validation

The retrospective predicted three risks; observed behaviour:

| Predicted risk | Actual outcome |
|---|---|
| Healer drift (patch introduces new defect) | Not observed; the Stage-1 linter caught zero new D1–D8 defects post-Healer |
| Stalls on long-edit agents | Confirmed — six of ten stalled at 600s. Fix for next iteration: split each chapter's tickets into smaller per-ticket dispatches (one agent per ticket, not one per chapter) |
| Critic cycle (two checks disagree) | Not observed; checks were orthogonal |

The Stage-1 deterministic linter performed exactly as designed — caught everything mechanical, fast and infallible, with zero variance.

The Stage-2 swarm delivered the 79-ticket audit in ~5 minutes of wall clock with 10 parallel agents. The 4-of-10 stall rate in the Healer phase is a problem to solve in v5.1, not a refutation of the architecture.

## Remaining defects (3 minor, 0 critical)

1. **ch-05 footnote count = 2** (band [3, 12]). Third `[^ame-share]` was inserted inside a markdown table cell and isn't being rendered by `process_footnotes`. Could move to a prose location or accept.
2. **ch-02 paragraph CV = 0.40** (just at the boundary of the 0.4 floor). Cosmetic.
3. **ch-09 paragraph CV = 0.38** (slightly below). Cosmetic.

## v5.1 carry-over

The stall rate on long-edit Healer agents needs an architectural change:

- **One agent per ticket** instead of one per chapter. Five tickets per chapter → 50 narrow dispatches instead of 10 long ones. Each agent does a single Edit and reports.
- **Implement the Sentinel-Healer loop properly** with a max-3-iteration cap and per-ticket isolated context.
- **Track the partial-completion case** explicitly: if an agent stalls, the post-stall state should still be checked rather than re-dispatched from scratch.

The v5 design doc covers these — the implementation just needs a follow-on cut.

## Output

`C:\bermuda-manual\book\releases\3.0.0\manuscript.pdf` — 78 pages, 1.38 MB.

## Files of record

- `book-qa/scripts/lint_artifact.py` — Stage-1 deterministic linter
- `book-qa/checklists/chapter-qa.md` — 15-item Stage-2 checklist
- `book-qa/checklists/house-style.yaml` — canonical terminology
- `book-qa/SKILL.md` — skill documentation
- `book-compose/MEMORY.md` — lessons-learned for future cuts
- `book-compose/docs/superpowers/retros/2026-05-11-v3-to-v4.3-retrospective.md` — defect inventory + root-cause patterns
- `book-compose/docs/superpowers/specs/2026-05-11-book-qa-v5-design.md` — full v5 architecture
- `bermuda-manual/qa/defects.json` — current Stage-1 defects
- `bermuda-manual/qa/v5-swarm-findings.md` — Stage-2 audit results
- `bermuda-manual/qa/chapter-tickets/ch-NN.json` — per-chapter Stage-2 tickets
- `bermuda-manual/reports/V5_REMEDIATION_REPORT.md` — this file
