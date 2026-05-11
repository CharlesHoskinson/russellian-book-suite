# v4.2 Tables Upgrade — Bermuda Manual

Run date: 2026-05-11

## Why

The v4.1 PDF rendered 13 tables as plain markdown — three-pixel borders, default sans-serif, no number formatting. They worked but looked like spreadsheets. Four of those tables (the two monthly budgets, the ARV-vs-permit matrix, and the insurance products) carry genuine comparison weight and deserved editorial treatment. The remaining nine reference tables (parishes, climate normals, governors, court tiers, GDP composition, ethnic and religious shares, education tiers, ferry routes) were fine as markdown but needed typography.

## Research outcome

Two parallel research agents surveyed Claude-skill catalogues and underlying libraries focused on tables. No dedicated table-skill exists in the Anthropic-official catalogue (`xlsx`/`docx`/`pptx`/`pdf` produce tables inside document containers, not as embeddable figures). Community surfaces (`travisvn/awesome-claude-skills`, `posit-dev/skills`, `karanb192`, `VoltAgent`, `glebis`, `davila7`) returned zero publication-table skills.

Library candidates evaluated: **great_tables** (Posit, MIT, v0.21.0), **plottable** (matplotlib-backed, MIT), **dataframe_image** (browser-dependent PNG), **pandas Styler** (LaTeX/HTML), **tabulate** (markdown emitter). The winning choice was **great_tables via `as_raw_html(inline_css=True)`** — it inlines all CSS into a self-contained HTML fragment, drops directly into the existing markdown → marked.js → Playwright pipeline, and brings spanner headers, source-note footnotes, `tab_style` row highlighting, and currency/percent formatters under one MIT licence.

Held: `plottable` for future heatmap tables; `D2`/`drawio` for future diagram alternatives; full skill stack (book-craft + plottable wrapper) still planned in the v4 design doc.

## What changed

**Installed locally:**

- `great_tables` 0.21.0 (Posit, MIT) and `css_inline` (MPL-2.0, required for `inline_css=True`).

**4 hero tables built via great_tables:**

| Table | Where | Treatment |
|---|---|---|
| Single-adult monthly budget | ch-06 | Currency formatter, share-of-total percent column, highlight on max-cost row (Rent), italicised total in source note. |
| Family-of-four monthly budget | ch-06 | Same as above, plus an editorial source note ("three times the single-adult budget for less than three times the consumption"). |
| ARV brackets vs. permit eligibility | ch-07 | Spanner header over licence fee columns (House / Condo), highlight on Bermudian / status-holder row. |
| Insurance products (HIP, FutureCare, GEHI, Private) | ch-09 | Source note explaining the SHB floor, highlight on FutureCare row. |

The hero-table HTML fragments are saved to `chapters/assets/shared/tables/*.html` and spliced into chapter drafts in place of the original markdown tables.

**9 reference tables re-themed via injected CSS:**

A new `<style id="md-table-theme">` block was added to `manuscript.html` before `</head>`. It applies serif typography (Georgia), booktabs-style rules (1.2px top + bottom, 1px header bottom, hairline body), tabular numerics, restrained padding, and shaded header row to every `<table>` rendered by marked.js. Print rules add `page-break-inside: avoid`.

## Output

`C:\bermuda-manual\book\releases\3.0.0\`

| Artifact | Size |
|---|---:|
| manuscript.pdf | 1.30 MB |
| manuscript.html | 756 KB |
| manuscript.md | 206 KB |

PDF: **76 pages**, 4 hero tables + 9 themed reference tables + 12 figures, no inline citation tokens, no claim-catalogue back matter.

## Versus prior cuts

| Cut | Pages | Visuals quality |
|---|---:|---|
| v2.0.0 | 53 | 0 figures, 0 styled tables |
| v3.0.0 (v4 fast-path) | 72 | 12 figures, plain markdown tables |
| v4.1 (visuals upgrade) | 73 | Mermaid diagrams + real-geometry maps + matplotlib charts |
| **v4.2 (tables upgrade)** | **76** | **+4 hero great_tables + 9 themed markdown tables** |

## Files of record

- Hero-table builder: `C:\tmp\build_hero_tables.py`
- Splicer: `C:\tmp\splice_hero_tables.py`
- Finalizer: `C:\tmp\finalize_v4_2.py`
- Hero-table HTML fragments: `C:\bermuda-manual\chapters\assets\shared\tables\`
- Updated chapter drafts: `C:\bermuda-manual\chapters\drafts\ch-06\`, `ch-07`, `ch-09`

## Carry-over for a future cut

- The remaining 9 reference tables could each be promoted to great_tables if there's appetite — climate normals (12-row × 4-column with month rownames) would benefit from row striping; ferry routes is essentially already a reference list and gains the most from CSS theming alone.
- The full v4 skill stack (book-craft skill with linters + visuals manifest + persona) is still scoped in `~/.claude/skills/book-compose/docs/superpowers/plans/2026-05-10-book-craft-v4-and-bermuda-regen.md`. v4.1 and v4.2 applied design patterns directly; the skill itself can be built when there's appetite for compounding the work into a reusable plugin.
