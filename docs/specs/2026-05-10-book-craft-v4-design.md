# v4: book-craft skill + Bermuda 75-page regen — Design

Date: 2026-05-10
Author: Charles (with Claude)
Status: Draft, pending user approval

## Goal

Lift the Russell-style book pipeline from "correct prose" to "a book worth reading." Add scene craft, structural variety (sidebars, tables, footnotes, enumerations), and visuals (charts, maps, photos, SVG). Apply the new pipeline to the Bermuda manual and expand it to 75 PDF pages with deeper, claim-backed content.

## Problem

The v3 Bermuda manual (`bermuda-manual:2.0.0`) is technically clean — Russell-style prose, no listicles, every paragraph claim-cited — but reads as soulless. Three symptoms:

1. Paragraph transitions land as hard cuts. The reader has no bridge between argument and argument.
2. Every block is prose. No tables, sidebars, footnotes, enumerations, or figures. A non-fiction book that contains *no* non-prose elements signals that no one made composition decisions at the page level.
3. No visuals — no charts, no maps, no photographs, no diagrams. A manual on Bermuda without a parish map is incomplete.

A fourth, deeper symptom: every chapter is approximately the same shape. Same paragraph length, same level of abstraction, same temperature. Nothing surprises. There is no authorial presence — no scene where the reader stands somewhere specific, sees something specific, hears the writer make a judgment.

A fifth, separate concern from the user: the manual is only ~53 pages. The depth target is **75 pages** (~20,000–22,000 words). Some chapters lose nuance the source documents support but the v3 draft compressed away.

## Architecture: five sibling skills

```
                  book-compose          (orchestrator: chapter compile, bundle, render)
                       │
       ┌────────┬──────┴──────┬────────────┐
       ▼        ▼             ▼            ▼
 russellian-  book-craft   book-knowledge  book-review
   style     (NEW v4)      (claim ledger)  (personas)
 (sentence    (chapter
   grain)     craft +
              visuals)
```

Boundaries:

- `russellian-style` — owns sentence-grain rules. v4 receives one small change: the listicle linter gains a `block-aware` mode that ignores content inside pandoc fenced divs.
- `book-craft` (new) — owns paragraph-and-chapter craft: transitions, scene density, structural variety, visuals manifest, narrative-craft persona.
- `book-knowledge` — unchanged structurally. New claim subtypes for visual assets (chart-data, map-region, photo-license). v4 regen also runs a claim-ledger expansion pass.
- `book-compose` v4 — pipeline plumbs `book-craft` linters and the visuals build step. Chapter contracts grow new acceptance tests.
- `book-review` v4 — registers `narrative-craft` as the sixth persona.

Data flow per chapter:
```
chapter contract → claim slice → draft → russellian + book-craft linters
→ resolve visuals manifest → build_visuals → persona reviews (6)
→ revision → bundle → book release
```

## Skill 1: `book-craft` (new)

Lives at `~/.claude/skills/book-craft/`. Mirrors the structure of `russellian-style` and `book-review`.

### Linters

`scripts/lint_transitions.py`
- Looks at every paragraph boundary in the chapter.
- For paragraph N and N+1, checks for: shared entity (same proper noun or anaphoric reference), explicit connective in the first 8 words of N+1, or a question-answer pattern.
- Output: per-boundary score 0/1 plus chapter aggregate `transition_quality = good_boundaries / total_boundaries`.
- Target: `transition_quality >= 0.7`.

`scripts/lint_scene_density.py`
- Counts concrete-scene markers per 1,000 words:
  - sensory verbs: taste, smell, hear, feel, watch, see, listen, touch
  - place markers at street-grain (named buildings, named streets, named beaches)
  - time-of-day cues: dawn, morning, afternoon, evening, dusk, night, at X o'clock
  - authorial-presence markers: you stand, you walk, you wait, you see
- Output: `scene_density` (scenes per 1,000 words).
- Target: `>= 2` for non-reference chapters, `>= 1` for `chapter_type: reference`.

`scripts/lint_structural_variety.py`
- Parses the chapter into blocks: prose paragraph, sidebar, table, footnote, enumeration, figure.
- Computes block-type histogram.
- Flags: >90% prose paragraphs (the v3 failure), or any single non-prose form >40% of non-prose blocks.
- Output: `structural_variety_index = 1 - prose_fraction`. Target `>= 0.15`.

`scripts/lint_soul.py`
- Composite tripwire combining: scene_density, uniform-paragraph-length penalty, figure count, sidebar count, structural variety.
- Output: `soul_score` in [0, 1]. Target `>= 0.6`.
- Surfaces the "soulless" signal pre-persona so revisions catch it early.

### Block-form library

`scripts/blocks.py`
- Recognizes six block types via pandoc fenced-div syntax:
  - `:::sidebar` — gray box with thin left border in print, callout card in HTML
  - `:::table` — tight typography, no zebra striping
  - `:::enumeration` — numbered list where order is categorical (not rhetorical)
  - `:::figure` — wraps `![alt](path){caption=..., source=clm-NNNN-NNNNNN}` with optional left/right float
  - `:::footnote` — endnote in PDF, marginal note in HTML
  - prose — the default
- `iter_blocks(text)` yields `(kind, body, span)`. Used by both `lint_structural_variety` and `russellian-style.lint_listicle_abstract` (block-aware mode).

### Visuals manifest

`scripts/visuals.py`
- Schema for `chapters/visuals/<chapter_id>.yaml`:
  ```yaml
  figures:
    - id: fig-01-parish-map
      kind: map
      claim_ref: clm-0042-000017
      caption: Bermuda's nine traditional parishes.
      alt_text: Map of Bermuda showing nine parishes in distinct colours.
      data: {parish_centroids: assets/bermuda-parishes.geojson}
    - id: fig-01-koppen
      kind: chart
      claim_ref: clm-0042-000023
      caption: Köppen-zone classification.
      data: {x: months, y: temp_high_low_mm_precip}
  ```
- Resolver: `build_visuals(workspace, chapter_id)` dispatches each entry by `kind` to:
  - `render_chart.py` (matplotlib, Russell-clean theme)
  - `render_map.py` (matplotlib + cached OSM/geojson, no external fetch at build)
  - `render_svg.py` (yaml schema → SVG; for org charts, pipelines, hierarchies)
  - photos: copied from `~/.cache/book-craft/photos/`
- Writes assets to `chapters/assets/<chapter_id>/`. Records license/source/claim in `chapters/assets/<chapter_id>/manifest.json`.

### Persona definition

`personas/narrative-craft.yaml`
- New sixth persona (joins gottlieb, lay-reader, domain-expert, copyeditor, enjoyment-reader).
- Voice: New Yorker / McPhee-trained editor with Bryson's ear for the comic detail.
- Focus areas: scene anchoring, authorial presence, transition craft, structural pacing, texture, figure placement.
- Severity rubric same as the other five.

### Reference docs

`references/`
- `block-forms.md` — when to use each form, examples.
- `visuals-playbook.md` — when a chart beats prose, when a map is required.
- `scene-craft.md` — how to weave Russell prose with McPhee scenes.

### Tests
~30 unit tests for the four linters + block parser + visuals resolver. ~10 fixture-based "good chapter" vs "bad chapter" tests. ~5 visual-render smoke tests (chart, map, svg).

## Skill 2: `russellian-style` v4 delta

Minimum change: `lint_listicle_abstract.py` gains a `--block-aware` mode (env var `RUSSELLIAN_BLOCK_AWARE=1`). Ignores content inside pandoc fenced divs (`:::sidebar`, `:::table`, `:::enumeration`, `:::figure`, `:::footnote`). Bullets outside any fence still trip.

- One helper added to `lint_common.py`: `iter_blocks(text)`.
- `book-compose.chapter_contract_check.py` sets the env var when invoking the linter.
- +3 tests covering inside-fence, outside-fence, env gating.

No other linter, principle, or test changes.

## Skill 3: `book-compose` v4 changes

### Contract template (`chapter-contract.template.yaml`)
New optional acceptance tests:
- `transition_quality >= 0.7`
- `scene_density >= 2` (waived for `chapter_type: reference`)
- `structural_variety_index >= 0.15`
- `visuals_required >= 2`
- `soul_score >= 0.6`

### Visuals build step (`scripts/build_visuals.py`)
- Runs after final draft, before bundling.
- Reads `chapters/visuals/<chapter_id>.yaml`, dispatches to `book-craft` renderers, writes to `chapters/assets/<chapter_id>/`.
- Bundle script copies the assets dir into the release bundle.

### HTML / PDF renderer block styling (`render_book_html.py`, print CSS)
- CSS classes for `.sidebar`, `.table`, `.figure`, `.footnote`, `.enumeration`.
- Print rules: `break-inside: avoid` for sidebars and figures; endnote-form footnotes in PDF; marginal-note-form in HTML.
- React book browser: figures jump-list in the TOC, lightbox for images.

### Pipeline orchestration (`run_chapter.py`)
Insert one step:
```
draft.md → linters (russellian + book-craft) → resolve visuals
→ build_visuals → persona reviews → revision loop → bundle
```

### Tests
+12 tests covering contract gates, visuals build dispatch, HTML/PDF block rendering, orchestration step ordering.

## Skill 4: `book-review` v4

One new persona file. No code changes — `dispatch_review.py` is persona-agnostic.

`personas/narrative-craft.yaml`:
- McPhee/Bryson-trained reviewer.
- Same severity rubric (critical/important/minor).
- +1 test verifying the persona loads and `aggregate_reviews` picks it up.

Dispatch math: 6 personas × 10 chapters = 60 dispatches per regen.

## Skill 5: `book-knowledge` v4

Structurally unchanged. New optional claim subtypes:
- `chart-data` — claim whose `data_payload` field carries the numeric series for a chart
- `map-region` — claim whose `data_payload` carries geo coordinates / shape
- `photo-license` — claim that records a photo's source URL, license, and attribution

Claim-ledger expansion sub-pass for the Bermuda regen (R8b-ii below) re-ingests the 13 source documents looking for previously-uncaptured verifiable claims.

## Bermuda v4 regen plan (release 3.0.0)

Target: 75 PDF pages, ~20,000–22,000 words, ~30 figures, ~15 sidebars, ~8 tables.

- **R8a — Visuals manifests**: subagent per chapter authors `chapters/visuals/<chapter_id>.yaml`. 2–4 figures per chapter targeted at the chapter's content. Sources reference existing claims.
- **R8b-i — Photo cache build (one-shot)**: Wikimedia Commons + NOAA + Bermuda Gov public-domain image fetch. ~30 images downloaded to `~/.cache/book-craft/photos/bermuda/` with licenses recorded.
- **R8b-ii — Claim ledger expansion**: re-ingest the 13 source documents looking for additional verifiable claims that support depth. Target +50–80 new claims. Ledger ends at ~270–300 claims.
- **R8c — Chapter revision against v4 contracts** (10 parallel subagent dispatches): each chapter grows to ~2,000 words. Per-chapter recipe:
  - 1 opening scene (concrete moment, sensory anchor)
  - 1 mid-chapter scene tied to a specific stakeholder
  - 2–3 sidebar definitions or asides (from existing parentheticals)
  - 2–4 figures inserted at points where data outruns prose
  - Expanded historical/policy framing where v3 compressed
  - Each new paragraph cites a verified claim — no fluff
  - Russell-grain prose untouched in non-scene passages
- **R8d — Build visuals**: `build_visuals.py` over all 10 chapters.
- **R8e — Linter sweep**: Russell linters + book-craft linters.
- **R8f — Persona reviews**: 60 dispatches, 6 personas × 10 chapters.
- **R8g — Targeted revision on criticals + style cleanup**.
- **R8h — Bundle, build book release 3.0.0, render PDF, regen report**.

Expected end state:
- 75 PDF pages
- ~30 figures across 10 chapters
- ~15 sidebars
- ~8 data tables
- 6-persona aggregate criticals: target <50 (vs 132 at v3 R3)

## Risks

- **Photo licensing thin.** If Wikimedia/NOAA coverage of Bermuda topics is sparse (likely for KEMH interior, specific government buildings, recent events), we accept fewer photos and lean on charts/SVGs.
- **Claim expansion may not yield 50–80 claims.** If source documents are already well-mined, expansion may yield fewer. Fallback: lower per-chapter word target to 1,800 and accept ~67 pages.
- **Subagent variance.** Scene-writing is harder than rule-following; some subagent outputs may fall flat. The `narrative-craft` persona is the safety net.
- **R8 is large.** Expect ~6 hours of wall-clock with parallel dispatch.

## Tests / acceptance

- All v3 tests stay green (russellian-style 59 + book-knowledge 58 + book-compose 78 + book-review 19 = 214).
- v4 adds ~45 new tests (book-craft ~30, russellian +3, book-compose +12, book-review +1).
- v4 regen success criteria:
  - manuscript.pdf >= 70 pages
  - total_word_count between 19,000 and 23,000
  - figure count >= 25
  - sidebar count >= 12
  - all chapters pass `structural_variety_index >= 0.15` and `soul_score >= 0.6`
  - 6-persona aggregate criticals <= 60

## Out of scope

- Audio / e-book / multi-language output
- LaTeX template work (existing pandoc path is enough)
- Interactive figures in the React browser beyond lightbox
- Genre-portability — adapting the stack for memoir, fiction, technical reference

## Open items

- License-check fallback path if Wikimedia returns no result for a topic
- Whether the React browser should show figures inline or only via lightbox
- Citation density on scene paragraphs — claim-per-sentence may be too strict; consider claim-per-scene
