# Feynman Corpus Map

The corpus gives `feynman-style` calibration anchors for each of the four rhetorical moves. The machine-readable index lives at `assets/feynman-corpus/index.json`. Each entry has a `source_id`, a `rhetorical_move`, and the text of the anchor.

## Entry types

**Short fair-use quotations** (`source_id` prefix `quote-`): verbatim short passages from Feynman's public lectures, the Challenger commission report, and interviews. These are the real thing — retrieve them when you need to calibrate tone and register.

**Synthetic before/after pairs** (`source_id` prefix `synthetic-`): authored pairs, not quotations. Each `-before` entry is a Russellized passage (dense, correct, atomic, cold); the corresponding `-after` entry shows the same passage after a Feynman pass. These are worked examples of the transformation, not attributable to Feynman. See `references/before-after-examples.md` for fuller commentary on the same pairs.

## Rhetorical move index

| `rhetorical_move` | What it means | When to retrieve |
|---|---|---|
| `analogy` | A concrete physical picture carries the logical content | The target passage explains an abstract relationship; the reader needs to see it, not just hear it defined |
| `direct-address` | "You," contractions, rhetorical questions, asides | The prose is correct but keeps the reader at arm's length; no "you," no questions, no conversational register |
| `honest-doubt` | Surface the puzzle; name what is genuinely unsettled | The passage covers contested ground, an approximation, or a result that should unsettle a careful reader but doesn't |
| `plain-restatement` | Say the same thing in shorter, plainer words | The passage uses Latinate vocabulary, multi-clause constructions, or jargon that a plain sentence would carry just as accurately |

## How to retrieve

Don't load the full index into a prompt by default. Identify which move is missing, then retrieve the one or two entries for that move. For a passage missing analogy, load `quote-imagine-small` and `synthetic-003-after`. For missing honest doubt, load `quote-nobody-understands-qm` and `synthetic-002-after`.

Use the retrieved entry as a register calibration — a reference for what the live move looks like. Do not imitate the diction. The question to ask is: what is the structural move this entry makes, and can I make the same structural move on the target passage?

## Current entry count

| `rhetorical_move` | Entries |
|---|---|
| `analogy` | 2 |
| `direct-address` | 3 |
| `honest-doubt` | 2 |
| `plain-restatement` | 6 |

The `plain-restatement` entries are the densest because they include the core Feynman statements that establish the overall register. The smaller `analogy` and `honest-doubt` pools are sufficient for calibration; expand them if sustained work on physics-heavy or technically contested prose reveals gaps.
