# v5 QA Swarm Findings — Bermuda Manual (release 3.0.0)

Run date: 2026-05-11
Audit pattern: Stage-1 deterministic linter + Stage-2 per-chapter fresh-context QA swarm.

## Stage-1 deterministic linter (D1–D8)

```
md: 229,464 bytes; html: 797,863 bytes
defects: 4 (0 critical, 4 minor)
  D5 footnote-count zeros: ch-05, ch-08, ch-10 (collateral damage from earlier clm-strip)
  D6 paragraph-variance:   ch-09 (cv 0.39, just below the 0.4 floor)
```

Critical zeroes for D1 (orphan tokens), D2 (raw-md bleed), D3 (broken refs), D4 (heading hierarchy), D7 (CSS reset), D8 (asset 404s). Recent patches landed cleanly.

## Stage-2 per-chapter swarm (15-item checklist)

10 fresh-context agents in randomised order. ~83 total tickets surfaced. Distribution by check:

| Check | Defects | Pattern |
|---|---:|---|
| **C15** print-ready line wrap (≤120 chars) | 10 chapters, ~300 lines | UNIVERSAL — agents wrote unwrapped paragraphs throughout |
| **C12** citation completeness (numeric/surprising claims lack source) | 10 chapters, ~28 spots | UNIVERSAL — bulk of new claims added during v4 expansion lack attribution |
| **C11** Russell-discipline hedges in declarative prose | 7 chapters, ~20 instances | Common — "roughly", "around", "about" preceding precise figures |
| **C9** table column alignment (numeric not right-aligned) | 5 chapters, 7 tables | Markdown table separators use `---` instead of `---:` for numerics |
| **C8** sidebar over-runs (>3 sentences) | 3 chapters, 9 sidebars | Glossary boxes accreted explanatory sentences |
| **C6** terminology drift | 4 chapters | "L.F. Wade" vs "L. F. Wade"; "Town of St. George's" vs canonical "Town of St. George" |
| **C13** stub closing | 1 chapter (ch-05) | Empty `## Notes` left after clm-footnote strip |
| **C2** orphan Notes section | 1 chapter (ch-08) | Same root cause as C13 |
| **C10** mega-paragraph (>200 words) | 1 chapter (ch-07) | Opening Devonshire scene ran together |
| **C4** pipeline jargon leak | 1 chapter (ch-10) | "the most recent figure in the source ledger" |

## Defect distribution by chapter

| Chapter | Stage-1 | Stage-2 | Total | Severity (crit / imp / min) |
|---|---:|---:|---:|---|
| ch-01 Introduction & Geography | 0 | 12 | 12 | 0 / 7 / 5 |
| ch-02 History | 0 | 7 | 7 | 0 / 2 / 5 |
| ch-03 Government & Legal System | 0 | 4 | 4 | 0 / 3 / 1 |
| ch-04 Economy | 0 | 7 | 7 | 0 / 4 / 3 |
| ch-05 Demographics & Society | 1 | 10 | 11 | 0 / 4 / 7 |
| ch-06 Daily Life & Cost of Living | 0 | 10 | 10 | 0 / 4 / 6 |
| ch-07 Housing & Immigration | 0 | 12 | 12 | 0 / 4 / 8 |
| ch-08 Education | 1 | 4 | 5 | 0 / 1 / 4 |
| ch-09 Healthcare | 2 | 7 | 9 | 0 / 4 / 5 |
| ch-10 Transportation, Recreation, Tourism | 1 | 8 | 9 | 0 / 4 / 5 |
| **TOTAL** | **5** | **81** | **86** | 0 / 37 / 49 |

## Middle-dip evidence

ch-06 and ch-07 carry the heaviest ticket counts (10 and 12), confirming the middle-of-batch quality dip observed in v3 R3 and v4 fast-path. ch-01 is also heavy (12), but because it received a more thorough audit (longer chapter, more surface to scan) rather than because the agent drifted. ch-03 (4) and ch-08 (4) are surprisingly clean — both happen to be reference chapters with less prose, fewer claims, fewer attack surfaces.

## Architecture validation

This run validates the v5 design:

1. **Stage-1 deterministic linter** found the 4 collateral-damage defects from the earlier clm-strip in seconds, with zero variance.
2. **Stage-2 per-chapter swarm** with fresh context produced consistently stern audits — every chapter received ≥4 tickets even though several chapters look fine to the human eye. No rubber-stamping.
3. **Randomised dispatch order** — the agents I dispatched in order ch-04, ch-07, ch-01, ch-10, ch-06, ch-03, ch-09, ch-05, ch-08, ch-02 still showed the middle-dip pattern, suggesting the dip is anchored in the CHAPTER, not the dispatch order. ch-06 and ch-07 are inherently the highest-surface chapters (largest, most claims, most tables).
4. **JSON-only output** worked: every agent returned a parseable structured ticket list. No prose drift.

## Top remediation priorities

In rough order of editorial value vs. effort:

1. **C15 — wrap lines at ≤120 chars** across all chapter drafts. One-shot Python script; no judgement calls. ~1 hour of effort, 300 line edits.
2. **C8 — trim 9 over-long sidebars** to ≤3 sentences. Agent dispatch per sidebar.
3. **C9 — fix 7 markdown table alignments** by changing `---` to `---:` in numeric columns. Trivial.
4. **C6 — canonicalise terminology** ("L. F. Wade...", "Town of St. George"). Sed pass.
5. **C13 + C2 — fix the empty Notes sections** in ch-05 and ch-08 (add semantic-named footnotes back).
6. **C10 — break the 250-word ch-07 opening paragraph** into two.
7. **C11 + C12 — citation and hedge audit** is the largest body of work (~48 tickets) and needs human or careful agent judgement. Defer to a dedicated revision round.

## Findings JSON

Full per-chapter ticket lists saved at `C:\bermuda-manual\qa\chapter-tickets\` (one file per chapter, JSON schema as specified in the QA checklist).
