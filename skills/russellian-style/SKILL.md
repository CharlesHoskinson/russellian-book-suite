---
name: russellian-style
description: Rewrite technical prose in Bertrand Russell's analytic style — lexical economy, logical atomism, declarative active-voice sentences, no hedging, axiomatic structure. Use when user says "apply Russell style", "rewrite in Russellian style", "tighten this prose", "remove hedging", "atomize this paragraph", "Russell pass on this draft", or asks to enforce signal density on a markdown passage. Do NOT use for marketing copy, fiction, persuasive essays, launch announcements, casual conversational drafts, or social media posts.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
---

# russellian-style

Rewrites technical prose in Bertrand Russell's analytic style and audits markdown for hedging, passive voice, modifier bloat, and rhythm defects. For authors of the book suite and anyone enforcing signal density on accuracy-bearing text.

## What it owns

- Sentence- and paragraph-level prose discipline.
- The Russellian style catalog and rule registry.
- Deterministic linters for hedges, passive voice, signal density, parallel structure, rhythm, and listicle abstraction.
- The `style-pass-report.md` artifact and its acceptance metrics.
- Refusal protocol for non-accuracy genres.

## What it does NOT own

- Source ingestion, claim ledgers, wiki synthesis — owned by `book-knowledge`.
- Chapter drafting, release bundles, PDF/EPUB rendering — owned by `book-compose`.
- Editorial persona reviews — owned by `book-review`.
- Question answering against a drafted manuscript — owned by `book-qa`.
- Generic AI-writing tells (em-dash overuse, rule-of-three, AI vocabulary) — owned by `humanizer`.

## Linters

- `scripts/lint_hedges.py` — hedge vocabulary detection against the rule registry.
- `scripts/lint_passive_voice.py` — passive constructions via spaCy dependency parse.
- `scripts/lint_signal_density.py` — adjective and adverb ratio per sentence against budget.
- `scripts/lint_parallel_structure.py` — grammatical-opening parity across bullet lists.
- `scripts/lint_sentence_rhythm.py` — sentence-length variance and cadence defects.
- `scripts/lint_listicle_abstract.py` — abstract-noun listicles masquerading as content.

## Style guide

`references/russellian-style-guide.md` is the authoritative catalog, organised across vocabulary, voice, atomicity, flow, and structure.

When prose is compliant but lifeless, read `references/russell-corpus-map.md` and compare against the 50-paragraph Russell corpus indexed in `assets/russell-corpus/index.json`.

## References index

- `references/russellian-style-guide.md` — authoritative style catalog.
- `references/russellian-vitality-guide.md` — vitality and rhythm rules for compliant-but-lifeless prose.
- `references/russell-corpus-map.md` — guide to the 50-paragraph Russell corpus.
- `references/how-i-write-maxims.md` — Russell's seven sentence-craft maxims.
- `references/logical-atomism-for-writers.md` — IF/AND IF/THEN decomposition for tangled conditionals.
- `references/before-after-examples.md` — worked rewrites paired with the rule each one applies.
- `references/section-headers.md` — taxonomy of section/subsection titles (four use / three ban categories) with the EpochPoET case study.
- `references/negative-triggers.md` — genres in which the skill refuses to activate.

## Composes with

- `book-knowledge` — ingests sources whose claims this skill later polishes.
- `book-compose` — calls this skill as the prose-polish stage of chapter drafting.
- `book-review` — runs persona reviews on prose already compliant with this skill.
- `book-qa` — queries chapters drafted under this style.
- `book-thesis` — provides reasoning layer for entailment-backed prose discipline.
- `humanizer` — strips residual AI-writing tells after this skill runs.

## Usage

- `/russellian-style` — invoke on the current selection or supplied path.
- "Apply Russell style to this paragraph" — single-passage rewrite.
- "Run the linters on chapter 3" — lint-only pass, no rewrite.
- "Russell pass on `draft.md`" — full pass with `style-pass-report.md`.

## Tests

Run with `pytest` from the skill root. Fixtures in `tests/fixtures/`; trigger calibration in `tests/trigger_tests.yaml`.
