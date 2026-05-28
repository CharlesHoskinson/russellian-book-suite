# Russell pass on the agentic-civilizations paper — design

- Date: 2026-05-27
- Status: approved in brainstorming; awaiting spec review
- Skill: `russellian-style` (the suite's prose-discipline skill)
- Target: `C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.md` (rewritten in place)

## Goal

Recast the agentic-civilizations paper in Bertrand Russell's analytic prose, in place, using the `russellian-style` skill and its linters as acceptance gates. Preserve every claim, citation, and structural element. Remove the epistemic-status tags and every other AI tell, and carry the certainty-versus-conjecture distinction in the prose itself, the way Russell did.

## The transformation

Rewrite every prose sentence in the paper in Russell's style: lexical economy, logical atomism (one claim per sentence), declarative active voice, axiomatic openings, dry precision, no hedging. Apply to all nine numbered sections and their prose. Tables, the reference list, and the section skeleton are containers; their prose contents are rewritten, their structure is kept.

## What gets stripped

- Every `(Grounded)`, `(Framework)`, `(Speculative)` tag, and every "reported" status label, throughout the document.
- The "Epistemic status and legend" section (it exists only to define those tags). Removing it does not disturb the numbered sections 1 through 9 or the References, since it sits before section 1.
- Hedging vocabulary ("it could be argued", "arguably", "somewhat", "may perhaps"), modifier bloat, passive constructions, inline-header bullet lists, and any "key insight" / scaffolding phrasing.
- AI-attribution of any kind. The commit message is terse and human, with no Co-Authored-By line.

## What is kept

- Every claim and fact in the paper. The Russell pass changes how things are said, not what is asserted.
- The numbered `[n]` citations and the References section. Standard scholarship, not a tell.
- The Agora Scale table (six rungs, "we are here" marker) and the nine-section structure.
- The dash-free constraint already in force (no em or en dashes).

## Carrying epistemics in prose, not tags

The paper currently leans on parenthetical tags to mark what is known versus conjectured. Russell carried that distinction in words, and so will the rewrite. Concretely:

- Where the paper tags a present-tense, sourced claim `(Grounded)`, the rewrite simply states it as fact, with its `[n]` citation.
- Where the paper tags a forward extrapolation `(Speculative)`, the rewrite marks the turn in prose: "Here I leave what is known for what may be guessed", "This is conjecture", "I do not know whether this will happen, but the direction is plain."
- Where a figure rests only on press report (the 100-agents-per-human forecast), the rewrite says so in a clause ("Huang asserts, and I have only the press report of it, that ..."), not with a "reported" tag.

The grounded-versus-speculative line is therefore sharper after the pass, not blurred. Russell separated knowledge from conjecture more cleanly than a tag does.

## Process

1. Rewrite the paper section by section, following `skills/russellian-style/references/russellian-style-guide.md` and comparing against the indexed Russell corpus (`assets/russell-corpus/index.json`, `references/russell-corpus-map.md`) when prose is compliant but flat.
2. Run the six linters against the rewritten file until each meets its budget:
   - `lint_hedges.py`, `lint_passive_voice.py`, `lint_signal_density.py`, `lint_parallel_structure.py`, `lint_sentence_rhythm.py`, `lint_listicle_abstract.py`.
   Emit a `style-pass-report.md` next to the paper recording the metrics.
3. Run a humanizer pass for residual AI tells; confirm zero em or en dashes.
4. Regenerate the PDF (`markdown` + `xhtml2pdf`, the existing A4 Helvetica build) and verify it is glyph-clean.
5. Commit in `C:\agenticcivthoughts` with a terse, human, AI-attribution-free message.

## Acceptance criteria

1. No `(Grounded)/(Framework)/(Speculative)` tag, no "reported" label, and no "Epistemic status and legend" section remain anywhere in the paper.
2. Every prose section reads in Russell's analytic voice; the six linters meet their budgets; `style-pass-report.md` is emitted.
3. Every claim, `[n]` citation, the References section, the Agora Scale table, and the nine-section structure are intact.
4. The certainty-versus-conjecture distinction is carried in prose; the speculative sections are marked as such in words.
5. Zero em or en dashes; no AI tells; the commit carries no AI attribution.
6. The PDF regenerates with no box, replacement, or dash glyphs.

## Out of scope

- A full book-suite workspace (`examples/`), chapters, or the multi-skill pipeline. This is a single-document Russell pass.
- Editing the v1 paper, the wiki, or any other agentic-civ file.
- Pushing to any remote.
