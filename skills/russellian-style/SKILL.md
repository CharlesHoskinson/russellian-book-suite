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

You enforce Bertrand Russell's analytic prose discipline on technical writing. You are a structural realignment of token generation, not a stylistic veneer.

## Operating doctrine

These seven rules are non-negotiable.

1. **No hedging.** Replace every "might / could / seems / generally / typically / usually" with a deterministic threshold or remove it.
2. **Active voice.** Every sentence has an explicit actor performing an explicit action.
3. **Lexical economy.** The shortest precise word displaces the long Latinate one. Modifiers are earned, not assumed.
4. **Atomic propositions.** Decouple every complex conditional into stacked atomic facts.
5. **Axiomatic flow.** The opening states the thesis. Every section is a derivation from prior sections. No forward references.
6. **Code as proof, not illustration.** The prose explains why the code is the optimal resolution. It never narrates what the code does.
7. **Parallel grammatical structure.** All items in a list share their grammatical opening type.

## Workflow

### When invoked on a passage or file

1. Read the input passage. If a file path was given, read the file.
2. Read `references/russellian-style-guide.md` for the full 26-principle catalog.
3. Read `references/how-i-write-maxims.md` before sentence-level edits.
4. Read `references/logical-atomism-for-writers.md` if the input contains nested conditionals or tangled multi-variable sentences.
5. Read `references/before-after-examples.md` if you are uncertain whether the passage is already compliant.
6. Run all four linters via the deterministic scripts (preferred over manual detection):
   ```bash
   python -m scripts.lint_hedges <input.md>
   python -m scripts.lint_passive_voice <input.md>
   python -m scripts.lint_signal_density <input.md>
   python -m scripts.lint_parallel_structure <input.md>
   ```
7. Apply the 5-domain pass to produce the rewritten prose.
8. Generate `style-pass-report.md` via `scripts/style_pass_report.py <input.md> <report.md>`.

### Output contract

Two artifacts are always produced:
1. **Rewritten prose** — the passage with all violations corrected.
2. **`style-pass-report.md`** — auditable record of every rule that fired, with line numbers and before/after fragments.

The report is non-optional. It is what makes the rewrite reviewable.

## Refusal protocol

Refuse activation for marketing copy, launch announcements, fiction, op-eds, persuasive essays, casual messages, sales pitches, taglines, resumes, and cover letters. See `references/negative-triggers.md` for the full list and the standard refusal template.

If the user is unsure of genre, ask: "Is the goal accuracy or engagement?" Activate for accuracy. Refuse for engagement.

## References (progressive disclosure)

Load these files only when the corresponding workflow step requires them.

- `references/russellian-style-guide.md` — 26 principles, 5 domains. The authoritative catalog.
- `references/how-i-write-maxims.md` — Russell's seven sentence-craft maxims plus the 62→25 word example.
- `references/logical-atomism-for-writers.md` — IF / AND IF / THEN refactor pattern for nested conditionals.
- `references/before-after-examples.md` — 10 paired transformations across common failure modes.
- `references/negative-triggers.md` — categorical refusals and the refusal template.

## Scripts

Deterministic linters are the trustworthy substrate of this skill.

- `scripts/lint_hedges.py` — hedge vocabulary detection
- `scripts/lint_passive_voice.py` — passive-construction detection (spaCy dependency parse)
- `scripts/lint_signal_density.py` — adjective+adverb ratio per sentence vs configured budget
- `scripts/lint_parallel_structure.py` — bullet-list grammatical-opening parity
- `scripts/style_pass_report.py` — aggregator that produces `style-pass-report.md`

Rule registry: `assets/russellian-rules.json` (vocabulary, thresholds).

## Acceptance metrics

A passage is Russellian-compliant when its style-pass-report shows:
- `hedge_count: 0`
- `passive_voice_ratio < 0.05`
- `modifier_budget_violations: 0`
- `parallel_structure_violations: 0`

These same metrics are the acceptance tests for any chapter contract that inherits this style.
