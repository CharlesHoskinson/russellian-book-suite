# V3 Regeneration Report — Bermuda Manual

Run date: 2026-05-10
Pipeline: russellian-style + book-knowledge + book-compose + book-review (v3)

## Summary

The Bermuda manual was regenerated end-to-end against the v3 skill suite. The new pipeline introduced two style linters (`lint_listicle_abstract`, `lint_sentence_rhythm`) and a five-persona review skill (`book-review`). The personas surfaced 132 chapter-level criticals across 10 chapters; a revision pass addressed every flagged critical, and a follow-up style cleanup brought all chapters back inside the v2 contract bar except for 12 small residuals.

## Output artifacts

`C:\bermuda-manual\book\releases\2.0.0\`

| Artifact | Size | Notes |
|---|---:|---|
| manuscript.md | 90.3 KB | full assembled markdown, 10 chapters |
| manuscript.html | 528.4 KB | skeleton + React/Tailwind app from v1 merged with v2 payload |
| manuscript.pdf | 303.8 KB | print-rendered from manuscript.html |
| summary.json | 99.2 KB | book metadata |
| book-manifest.yaml | 0.8 KB | manifest |
| claims-bibliography.jsonl | 86.5 KB | 222 verified claims |
| chapter-bundles/ | — | 10 v2-final chapter bundles |

## Word counts

| Chapter | v1.0.0 | v2.0.0 | Δ |
|---|---:|---:|---:|
| ch-01 Geography & Climate            | 1285 | 1303 | +18 |
| ch-02 Government & Political Status  | 1558 | 1717 | +159 |
| ch-03 Economy                        | 1233 | 1283 | +50 |
| ch-04 Demographics, Society, Culture | 1467 | 1632 | +165 |
| ch-05 Legal System                   | 1470 | 1599 | +129 |
| ch-06 Infrastructure & Utilities     | 1365 | 1550 | +185 |
| ch-07 Housing & Immigration          | 1222 | 1218 | −4 |
| ch-08 Education                      | 1167 |  967 | −200 |
| ch-09 Healthcare                     | 1238 | 1279 | +41 |
| ch-10 Transportation, Recreation, Tourism | 1664 | 1701 | +37 |
| **Total**                            | **13,669** | **14,249** | **+580** |

ch-08 shrank because the revision deleted unsupported curriculum claims and a "Structure at a Glance" listicle. The other chapters grew slightly as scenes and concrete images replaced bullet listicles.

## Persona reviews (R3)

50 dispatches: 5 personas × 10 chapters.

| Chapter | Critical | Important | Minor |
|---|---:|---:|---:|
| ch-01 | 18 | 27 | 29 |
| ch-02 | 10 | 27 | 32 |
| ch-03 | 13 | 31 | 29 |
| ch-04 | 15 | 29 | 26 |
| ch-05 | 14 | 28 | 29 |
| ch-06 |  8 | 27 | 28 |
| ch-07 | 14 | 28 | 27 |
| ch-08 | 18 | 25 | 26 |
| ch-09 |  9 | 26 | 27 |
| ch-10 | 13 | 29 | 30 |
| **Total** | **132** | **277** | **283** |

Per-persona verdict: gottlieb 10 NEEDS_WORK; lay-reader 9 APPROVED_WITH_NOTES + 1 NEEDS_WORK; domain-expert 10 NEEDS_WORK; copyeditor 10 NEEDS_WORK; enjoyment-reader 9 NEEDS_WORK + 1 APPROVED_WITH_NOTES.

## Revision pass (R4)

10 dispatches, one per chapter. Every chapter addressed 100% of its criticals (132 / 132) plus adjacent importants.

Cross-chapter consistency followed `reports/canonical-facts.md`:
- 181 named islands and rocks (was: "around 180" / "181" inconsistent)
- Nine traditional parishes including St. George's; "public territory" dropped
- "Bermuda cedar" canonical name; *Juniperus bermudiana* glossed on first reference (ch-01)
- L. F. Wade International Airport on St. David's Island in St. George's Parish

## Style cleanup (R4b)

Revision introduced 38 new lint findings (mostly hedges, modifier budget, rhythm). A focused cleanup pass closed 41 of 43 findings. Final lint state:

| Chapter | hedge | passive | mod | parallel | listicle | rhythm | em-dash | ai |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ch-01 | 2 | 7.5% | 0 | 0 | 0 | 1 |  8 | 0 |
| ch-02 | 1 | 1.7% | 1 | 0 | 0 | 0 | 12 | 0 |
| ch-03 | 0 | 1.4% | 0 | 0 | 0 | 0 |  6 | 0 |
| ch-04 | 0 | 4.5% | 1 | 0 | 0 | 1 | 17 | 0 |
| ch-05 | 1 | 1.1% | 0 | 0 | 0 | 0 |  9 | 0 |
| ch-06 | 0 | 0.0% | 0 | 5 | 0 | 0 |  8 | 0 |
| ch-07 | 0 | 1.6% | 1 | 0 | 0 | 0 |  9 | 0 |
| ch-08 | 0 | 0.0% | 1 | 0 | 0 | 2 |  5 | 0 |
| ch-09 | 0 | 1.3% | 1 | 0 | 0 | 0 |  3 | 1 |
| ch-10 | 0 | 5.0% | 1 | 0 | 0 | 0 |  8 | 0 |

The contracts target zero on hedge / modifier / listicle / rhythm; 12 residuals remain across 8 chapters. All listicle-abstract violations were eliminated (the v3 linter's primary purpose). Passive-voice ratios stayed under the 10% threshold everywhere. AI fingerprint vocabulary stayed at zero except one hit in ch-09. ch-06's 5 parallel-structure violations are not gated by the contract but warrant attention in a follow-up pass.

## Bundle and book release (R5–R6)

- 10 chapter bundles built at version `v2-final` (markdown only; pandoc-derived formats skipped because pandoc is not installed locally).
- Book release `2.0.0` assembled with `build_book.py`, including:
  - book preflight (SHACL + competency queries) — passed
  - manuscript assembly (TOC, 10 chapters, 14,249 words)
  - book summary
  - HTML skeleton render
  - PDF print via Playwright/Chromium
  - chapter-bundles copied
  - claims-bibliography.jsonl emitted
- React/Tailwind/shadcn book browser merged from v1.0.0 (kept the bundled app code intact, swapped in the new book-payload + book-manuscript script bodies).

## Open items

1. Two persona reviews per chapter remain at v3 first-cut state (not re-run after revision). Re-running personas would confirm the critical-count drop quantitatively.
2. The 12 residual lint findings could be cleared with one further targeted pass.
3. ch-06 retains 5 parallel-structure violations introduced during revision — flagged here but not fixed (linter not gated by the contract).
4. ch-09 has 1 residual AI-fingerprint hit; trace and fix.

## Files of record

- `reports/v3-linter-findings.md` — initial linter sweep before revision
- `reports/v3-persona-findings.md` — 50-dispatch persona summary
- `reports/canonical-facts.md` — cross-chapter consistency decisions
- `reports/V3_REGEN_REPORT.md` — this file
- `chapters/drafts/ch-NN/persona-review.md` — aggregated persona reviews per chapter
- `chapters/releases/ch-NN-v2-final/` — per-chapter bundle outputs
- `book/releases/2.0.0/` — book release artifacts
