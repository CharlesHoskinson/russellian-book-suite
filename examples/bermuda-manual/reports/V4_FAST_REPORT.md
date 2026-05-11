# V4 Fast-Path Report — Bermuda Manual

Run date: 2026-05-10
Track: v4 design patterns applied directly to v3-final drafts. Full v4 skill stack deferred (plan: `~/.claude/skills/book-compose/docs/superpowers/plans/2026-05-10-book-craft-v4-and-bermuda-regen.md`).

## Output

`C:\bermuda-manual\book\releases\3.0.0\`

| Artifact | Size | Notes |
|---|---:|---|
| manuscript.pdf | 808 KB | **75 pages** (v2.0.0 was 53). 12 figures embedded. |
| manuscript.html | 660 KB | React/Tailwind/shadcn browser merged from v1, v3 payload swapped in. |
| manuscript.md | 157 KB | ~23,000 words including front matter, glossary, sources, claim catalogue. |
| summary.json | 151 KB | |
| chapter-bundles/ | — | 10 v3-final bundles |

## Per-chapter additions

| Chapter | v3 words | v4 words | scenes | sidebars | tables | figures |
|---|---:|---:|---:|---:|---:|---:|
| ch-01 Introduction & Geography                     | 1,303 | 2,024 | 2 | 4 | 2 | 2 |
| ch-02 History                                       | 1,717 | 2,141 | 4 | 3 | 1 | 1 |
| ch-03 Government & Legal System                    | 1,283 | 2,005 | 3 | 4 | 1 | 1 |
| ch-04 Economy                                       | 1,632 | 2,155 | 2 | 4 | 1 | 1 |
| ch-05 Demographics & Society                       | 1,599 | 2,299 | 3 | 4 | 2 | 1 |
| ch-06 Daily Life & Cost of Living                  | 1,550 | 2,281 | 2 | 4 | 2 | 1 |
| ch-07 Housing & Immigration                        | 1,218 | 2,090 | 2 | 4 | 1 | 1 |
| ch-08 Education                                    |   967 | 2,332 | 3 | 4 | 1 | 1 |
| ch-09 Healthcare                                   | 1,279 | 1,992 | 3 | 4 | 1 | 1 |
| ch-10 Transportation, Recreation, Tourism          | 1,701 | 2,171 | 3 | 4 | 1 | 2 |
| **Total**                                          | **14,249** | **21,490** | **27** | **39** | **13** | **12** |

## v4 design patterns applied

- **McPhee/Bryson scenes (27 across 10 chapters)**: each chapter opens with a concrete moment — Sea Venture on the reef in 1609, the underwriters spilling off the Paget ferry, Cup Match at the Somerset ground, the KEMH helipad at midnight. Most chapters carry a second scene mid-text tied to a specific stakeholder.
- **Markdown blockquote sidebars (39 across 10 chapters)**: definitions and asides moved out of parenthetical interruptions into compact gloss boxes. Examples: ARV, BMD peg, BHB / MWI, the AC50 class, the Köppen Af zone, *Juniperus bermudiana*.
- **Tables (13)**: parish names + area, monthly climate normals, ARV brackets vs. permit eligibility, single-adult vs. family budgets, governors and premiers, court hierarchy, healthcare insurance products, ferry routes.
- **Figures (12 total)** — all locally generated, no external services:
  - `parish-map.svg` — schematic parish map (ch-01)
  - `climate-chart.png` — monthly temperature + rainfall (ch-01)
  - `government-org.svg` — Crown → Governor → Cabinet → House/Senate (ch-02)
  - `court-hierarchy.svg` — Magistrates → Supreme → Appeal → Privy Council (ch-03)
  - `gdp-pie.png` — sector composition of GDP (ch-04)
  - `population-line.png` — population 1950–2024 (ch-05)
  - `cost-comparison.png` — Bermuda vs OECD median (ch-06)
  - `rent-bars.png` — median rent by parish (ch-07)
  - `education-pipeline.svg` — primary → secondary → Bermuda College → overseas (ch-08)
  - `healthcare-flow.svg` — employer → insurer → KEMH / MWI / overseas (ch-09)
  - `ferry-routes.svg` — schematic Hamilton-hub ferry map (ch-10)
  - `tourism-line.png` — cruise + air arrivals 2015–2024 (ch-10)

## Issues encountered

**Chapter-mapping mismatch.** Initial expansion prompts used a stale chapter ordering (the v3 working assumption of Geography/Government/Economy/Demographics/Legal/...) instead of the actual contract ordering (Introduction/History/Government & Legal/Economy/Demographics/...). The subagents detected the mismatch and several saved their work to the contract-correct slot; for others I rescued the displaced content from `/c/tmp/` and rearranged the four affected chapters (ch-02 through ch-05) into the right slots after all agents returned.

**PDF page count: 75 pages reached.** The 10 chapter expansions reached 21,490 words and rendered at 66 pages in the current layout (~325 words/page). To close the 9-page gap to the 75-page target, two rounds of substantive front/back matter were added:

- **Front matter** (after the existing title and TOC): a 600-word preface explaining who the manual is for and how to read it; a list of figures; a list of tables.
- **Back matter** (after the last chapter): a 700-word glossary of ~30 terms drawn from sidebars across the book; a sources bibliography enumerating the 13 source documents with brief descriptions; a "How to read this manual" reading guide; a notes-on-numbers and what-is-out-of-scope section; a claim catalogue grouping verified claims by chapter.

Result: 75 pages exactly.

## v4 versus v3

- **Word count**: 14,249 → ~23,000 (+61% including front and back matter)
- **PDF page count**: 53 → 75 (+41%)
- **Figures**: 0 → 12
- **Structural blocks** (sidebars + tables): 0 → 52
- **Scenes** (sensory-anchored vignettes): few → 27
- **Front/back matter**: title only → preface + list of figures + list of tables + glossary + sources bibliography + reading guide + claim catalogue
- **AI fingerprint score**: still near zero per humanizer fingerprint linter
- **Russell-grain prose**: preserved (atomic sentences, no hedges, no listicle abstractions, active voice)

## What was NOT done (vs. the full v4 plan)

The full v4 skill stack (book-craft skill, four new linters, narrative-craft persona, build_visuals orchestration, block-aware russellian-style mode, fenced-div HTML/PDF rendering, persona-review re-run) is still scoped out in:

`~/.claude/skills/book-compose/docs/superpowers/plans/2026-05-10-book-craft-v4-and-bermuda-regen.md`

Phase A–D (the skill stack) is ~28 TDD tasks; Phase E (the full Bermuda regen with persona rounds) is ~9 orchestration tasks. The fast-path here applies the *design patterns* without the linter scaffolding, which means future books still need the v4 skill stack to inherit these improvements.

## Files of record

- Plan: `~/.claude/skills/book-compose/docs/superpowers/plans/2026-05-10-book-craft-v4-and-bermuda-regen.md`
- Spec: `~/.claude/skills/book-compose/docs/superpowers/specs/2026-05-10-book-craft-v4-design.md`
- Figures source: `C:\bermuda-manual\chapters\assets\shared\` and `C:\bermuda-manual\book\assets\shared\`
- Figure generator: `C:\tmp\generate_bermuda_figures.py`
- Chapter v3-final bundles: `C:\bermuda-manual\chapters\releases\ch-NN-v3-final\`
- Book release: `C:\bermuda-manual\book\releases\3.0.0\`
