# feynman-style — second-pass readability layer (design)

**Date:** 2026-06-02
**Status:** approved (design); ready for implementation plan
**Skill home:** `C:\russellian-book-suite\skills\feynman-style\`

## Purpose

`feynman-style` rewrites prose that has already passed `russellian-style` so that it
*clicks* for a reader. Russell makes prose correct, atomic, and hedge-free; the result is
elegant but often dense and hard to read. `feynman-style` runs **second**, on the
Russellized text, and warms the surface — concrete analogy, conversational directness,
honest curiosity, and plain playful diction — without disturbing the argument Russell
established.

It is named for Richard Feynman, whose teaching voice is the target register: explain a
hard thing simply, in everyday pictures, talking *to* the reader. The skill is a
structural twin of `russellian-style` (prompt-only voice modes + deterministic linters +
corpus-backed calibration + a refusal protocol), with one new component — a preservation
check that guarantees the Feynman pass did not alter the logic.

## Pipeline position and the two-layer contract

Feynman is a **second pass**. `book-compose` gains an optional `feynman` stage that runs
**after** the Russell stage, never before. Run standalone, it operates on any
already-tightened passage.

The governing contract is two-layer:

- **Feynman owns the prose surface.** It may freely re-introduce things Russell removes:
  rhetorical questions, asides, contractions, direct address, "now you might ask—",
  honest-doubt framing.
- **Russell owns the argument skeleton.** Feynman must NOT alter claims, claim accuracy,
  logical structure, or atomic argument order. `preserve_argument` enforces this half as a
  hard gate.

This separation is what lets two opposing style philosophies compose instead of fight.

## Voice traits (what the skill enforces and rewards)

All four are core, drawn from the Feynman corpus:

1. **Concrete analogy & physical intuition** — replace abstraction with tangible pictures
   ("jiggling atoms", "wobbling plates"). The signature move.
2. **Conversational directness** — first/second person, contractions, rhetorical
   questions, asides. Talks to the reader like a lecture.
3. **Curiosity & honest doubt** — foregrounds the puzzle, admits what is not understood,
   models thinking out loud ("the funny thing is…", "nobody really knows why").
4. **Playful, plain diction** — short Anglo-Saxon words over Latinate jargon; humor;
   deflates pomposity; low reading-grade load without dumbing down.

## Non-destruction contract (Russell linters must not eat Feynman's work)

The central pipeline risk: if downstream gates (`book-qa`'s release-gate, or anyone
re-running `russellian-style`) apply Russell's **surface** rules to Feynman-final prose,
they flag every analogy aside, rhetorical question, contraction, and honest-doubt marker
as a violation — and a "fix" reverts exactly the work Feynman just did. Three layered
mechanisms prevent this.

### 1. Partition all linters into Surface vs Integrity

Every linter — Russell's and Feynman's — is tagged in `feynman-rules.json`:

| Class | Linters | Runs on Feynman-final prose? |
|---|---|---|
| **Surface** (Feynman legitimately overrides) | `lint_hedges`, conversational/rhetorical-question bans, `lint_signal_density` (Russell-calibrated), `lint_sentence_rhythm` (Russell-calibrated), `lint_ai_staccato` | **No** — skipped |
| **Integrity** (always enforced, both passes) | claim accuracy, citations/footnotes, `preserve_argument` (atomic structure + claim survival), parallel structure within lists | **Yes** |

Honest-doubt markers ("nobody really knows why") are explicitly classified as Feynman
**curiosity moves**, not Russell **hedging** — so the hedge linter is precisely one of the
surface linters skipped on Feynman-final text.

`feynman-rules.json` holds the **classification map** (linter name → `surface | integrity`
→ which stage it gates), not a re-implementation. The Russell-owned linters continue to
live in `russellian-style` and are reached, when needed, via `sibling_skills`; the
partition only decides which of them are allowed to run on Feynman-final prose.

### 2. Stage provenance + terminality

Feynman is **terminal** for surface dimensions. `book-compose` ordering enforces
Russell → Feynman, never the reverse. Feynman-passed sections carry a provenance/stage
marker so `book-qa`'s chapter-contract-check, on Feynman-final text, runs **only the
integrity set + Feynman's own budgets** — never the surface Russell budgets.

### 3. `preserve_argument` is the safety net that makes (1) and (2) sound

Because it independently guarantees claims and argument structure survived the Feynman
pass, the surface Russell checks can be switched off without losing the thing that
matters. Integrity is gated; surface is handed to Feynman.

### Sibling touch points (scoped, not silent scope creep)

- `book-compose`: add the optional terminal `feynman` stage and enforce Russell → Feynman
  ordering.
- `book-qa`: per-stage linter selection — Feynman-final text validated against
  integrity-set + Feynman budgets only.

These are surgical edits to two sibling skills, scoped explicitly in the plan.

## Architecture

A structural twin of `russellian-style`. Prompt-only voice modes do the rewriting;
deterministic spaCy linters score the result; a Burrows-Delta profile calibrates against
the corpus; `preserve_argument` is the one hard gate.

### Directory structure

```
skills/feynman-style/
├── SKILL.md                      # frontmatter + contract + triggers + refusal protocol
├── skill_api.py                  # API_VERSION=(0,1); lint_fragment(); LintIssue; preservation entry
├── pyproject.toml                # spacy>=3.7,<4.0, pyyaml, jsonschema, pytest
├── pytest.ini
├── assets/
│   ├── feynman-rules.json        # linter registry + Surface/Integrity partition + budgets
│   ├── feynman-delta-profile.json# calibration profile built from the corpus
│   ├── ai-vocabulary-supplement.json  # ported/extended AI-slop list
│   ├── style-pass-report.template.md
│   ├── system-prompts/
│   │   ├── technical-exposition.md   # "explain a hard thing simply" (primary)
│   │   ├── pedagogical-walkthrough.md# lecture/teaching cadence
│   │   └── popular-science.md        # general-audience narrative
│   └── feynman-corpus/
│       └── index.json            # anchor paragraphs: {source_id, line_hint, rhetorical_move, text}
├── scripts/
│   ├── lint_common.py            # shared sentence iter + rules loader (ported)
│   ├── lint_analogy_density.py   # rewards concrete/physical analogies per N sentences
│   ├── lint_concreteness.py      # abstract-noun ratio; flags un-grounded abstraction
│   ├── lint_reading_grade.py     # Flesch-Kincaid / syllable load; flags too-hard
│   ├── lint_latinate_diction.py  # flags Latinate jargon where an Anglo-Saxon word exists
│   ├── lint_conversational.py    # detects/rewards direct address, questions, contractions
│   ├── lint_curiosity_markers.py # rewards honest-doubt / puzzle-framing moves
│   ├── lint_sentence_rhythm.py   # cadence/burstiness (ported, recalibrated to Feynman)
│   ├── lint_ai_vocabulary.py     # ported AI-slop guard
│   ├── score_feynman_delta.py    # Burrows-Delta vs feynman-delta-profile.json
│   ├── delta_math.py             # ported
│   ├── build_delta_profile.py    # OPTIONAL offline profile from local corpus-raw/ drop (no network)
│   ├── preserve_argument.py      # NEW: checks claims/structure survived the pass (hard gate)
│   └── system_prompt_loader.py   # ported
├── references/
│   ├── feynman-style-guide.md    # the moves: analogy, address, doubt, plain diction
│   ├── feynman-vitality-guide.md # when prose is plain but lifeless
│   ├── feynman-corpus-map.md     # corpus index by rhetorical move
│   ├── before-after-examples.md  # Russell-output → Feynman-output worked rewrites
│   └── negative-triggers.md      # refusal protocol + Surface/Integrity partition doc
└── tests/
    ├── unit/                     # one test module per linter, fixtures-driven
    ├── fixtures/
    └── integration/              # russell-output → feynman pass → preserve check
```

The only genuinely new component versus `russellian-style` is `preserve_argument.py`.
Everything else is port-and-recalibrate.

## Public API

Mirrors `russellian-style`:

```python
API_VERSION = (0, 1)

lint_fragment(text: str, linters: Optional[list[str]] = None) -> list[LintIssue]
# LintIssue: dataclass(linter, line, col, message)

preserve_argument(before: str, after: str) -> PreservationReport
# the hard gate: did claims / atomic structure survive the rewrite?
```

Default linters = the Feynman reward/penalty subset. Surface Russell linters are reachable
but excluded from the Feynman-final default set.

## Corpus / calibration (feature-based, no bulk scraping)

**Decision (2026-06-02):** the bulk-download plan is dropped. The one cleanly-fetchable
source — *The Feynman Lectures on Physics* (`feynmanlectures.caltech.edu`) — declares
`Content-Signal: search=yes,ai-train=no` and `Disallow: /` for all AI crawlers, an express
reservation of rights under EU Directive 2019/790 Article 4. No Feynman writing is in the
public domain (he died in 1988; the Lectures, the Messenger Lectures, the memoirs, and the
essays are all under copyright). Scraping any of it to build an AI-style corpus violates
both the rightsholder's express reservation and the `scrapling-fetch` doctrine ("honor
robots.txt — non-negotiable"). The skill therefore calibrates on **structural features**,
not on a verbatim corpus.

The Feynman pass works from stylometric features measured on the *rewrite itself*, which
need calibrated thresholds, not held source text:

- analogy / concrete-instance density per N sentences,
- reading-grade load (Flesch-Kincaid / syllable count),
- contraction and rhetorical-question rate,
- Latinate-vs-Anglo-Saxon diction ratio,
- curiosity / honest-doubt marker frequency.

Anchors and thresholds come from two committed, copyright-clean sources:

- **`assets/feynman-corpus/index.json`** — a small set (~12–20) of *short fair-use
  excerpts* (sentence-to-short-paragraph length, the length any essay about Feynman
  quotes) tagged by rhetorical move (analogy, direct-address, honest-doubt,
  plain-restatement), plus **synthetic before/after pairs** we author (dense Russellized
  input → Feynman-warmed output). These illustrate moves; they are not a reproduction of
  any work.
- **`assets/feynman-delta-profile.json`** — feature thresholds (the ranges above),
  hand-set from the fair-use anchors and from documented descriptions of Feynman's style,
  not derived from a scraped frequency count.

**Optional local-drop frequency profile (no network).** If the user owns digital copies,
`build_delta_profile.py` reads files the user places in a local `corpus-raw/` drop folder
and writes a frequency profile *locally* for private calibration. The folder is
git-ignored; raw text is never committed. This path is entirely offline — it uses no
network and therefore never touches `scrapling-fetch`. It is optional: with no drop folder
present, the skill calibrates from the committed feature thresholds alone.

The skill ships and functions with zero network access. `scrapling-fetch` is **not** a
dependency of `feynman-style`.

## Testing and error handling

- **Per-linter unit tests**, fixtures-driven (positive + negative), one module each — TDD,
  mirroring `russellian-style/tests/unit/`.
- **Integration test (proves the non-destruction contract):** a known Russell-output
  fixture → Feynman pass → assert (a) Feynman budgets met, (b) `preserve_argument`
  confirms claims/structure intact, (c) surface Russell linters are correctly skipped.
- **`preserve_argument` tests:** a deliberately argument-breaking rewrite must be caught.
- **Error handling:** linters are candidate-detectors with budgets (not hard zero gates),
  same as Russell; `preserve_argument` is the one hard gate. The skill runs fully offline;
  `build_delta_profile.py` handles a missing/empty `corpus-raw/` drop folder by falling
  back to the committed feature thresholds rather than erroring.

## Refusal protocol

Declared in `references/negative-triggers.md`. The skill refuses on text where Feynman's
warmth is inappropriate: formal proofs, legal/specification text, API reference,
bureaucratic boilerplate, and academic abstracts. It also refuses to run *before*
`russellian-style` (it is a second pass by contract).

## Out of scope for v0.1

- Ingesting copyrighted memoir/essay text the user has not supplied locally.
- A configurable Feynman-intensity dial (light/medium/full). The contract is fixed:
  Feynman overrides surface, Russell wins on logic.
- Non-English prose.
