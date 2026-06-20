---
name: triadic-voice
description: >
  Generate or rewrite prose in a fused writing voice — Bertrand Russell's analytic rigor,
  Richard Feynman's intuition-first warmth, and Charles Hoskinson's candor and momentum —
  grounded in a committed corpus of Hoskinson's real transcribed speech. Runs entirely inside
  the Claude session: you, the running model, ARE the generator. No API key, no external model
  call. Use this whenever the user wants to write, draft, generate, or rewrite something "in
  Charles's voice", "in Hoskinson's voice", "in the triadic voice", "in the Russell/Feynman/
  Hoskinson blend", or asks for a post, essay, explainer, announcement, or passage in that
  style — even if they don't name the skill. Also use when the user wants pure-Hoskinson voice
  on its own. Do NOT use for generic marketing copy, unrelated authors, or code.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
---

# triadic-voice

You write in a fused voice built from three real exemplar corpora. You do the writing yourself,
here in the session — there is no API to call and no key to set. The earlier mistake this skill
corrects was wiring generation to an external model endpoint; that is only for unattended batch
runs. In a normal session the model reading this skill is the one that writes.

## The three voices

| Voice | Contributes | Source |
|---|---|---|
| Russell | analytic rigor, logical atomism, one exact claim per sentence, no hedging | `../russellian-style/assets/russell-corpus/index.json` (public domain) |
| Feynman | concrete analogy, intuition before formalism, "let me show you why", warmth | `../russellian-style/assets/feynman-corpus/index.json` (pointers only — never quote verbatim) |
| Hoskinson | candor, direct address, forward momentum, systems-design framing, domain authority | `../russellian-style/assets/hoskinson-corpus/index.json` (his own transcribed words, inline) |

The fusion contract lives in `../russellian-style/references/triadic-voice-guide.md`. Read it.

## How to generate (in-session, no key)

1. **Pick the mode.** `hoskinson` for pure Charles Hoskinson voice; `triadic` for the three-voice
   fusion. Default to whatever the user asked for; if unspecified, `triadic`.
2. **Ground yourself in the real voice.** Read `triadic-voice-guide.md`, then read 6–10 entries
   from `hoskinson-corpus/index.json` whose `rhetorical_move`/`tags` fit the topic. These are his
   actual words — study the cadence, candor, and signature moves, do not copy the sentences. For a
   fuller sense of rhythm, skim a transcript or two under `hoskinson-corpus/transcripts/`.
3. **Write the passage** (default 150–220 words; follow the user's length if they give one):
   - **Open with Hoskinson** — state the stakes plainly, with candor and direct address.
   - **Develop with Feynman** — build the intuition from scratch and show *why* before any
     formalism, with warmth.
   - **Close with Russell** — compress to one exact, unhedged, declarative claim.
4. **Clear the discipline floor.** The `russellian-style` linters are the quality bar regardless of
   voice: active voice, no hedging, signal density (restraint on adjectives/adverbs), varied
   sentence rhythm. Warmth and momentum are welcome; a hedge or a lazy passive is not.

### Optional helper

If you want the exact corpus-grounded prompt assembled for you (e.g. to hand to a fresh context or
a headless run), `tools/build-voice-corpus/scripts/generate.py` builds it:

    python -m scripts.generate --topic "..." --mode triadic   # prints the prompt; no key, no deps

It only *prints* the prompt by default. An Anthropic-backed mode (`--llm anthropic`) exists for
unattended batch runs and needs the optional `[api]` extra plus a key — you do not need it here.

## Avoid the formula (this is the hard part)

A three-part chassis becomes a template fast. Across more than one passage, vary deliberately:

- **Openings** — rotate among stating the stakes, a hostile objection, a concrete scene, a flat
  definition, and a contradiction. Do not open two passages the same way.
- **Feynman development** — it is a *method*, not an analogy slot. Rotate among analogy, a worked
  example, a counterexample, a failure case, a toy model, and a step-by-step derivation. Do not
  reach for "imagine…" / "picture…" / "think of…" every time.
- **Russell close** — rotate among an exact definition, a boundary condition, a causal claim, a
  necessary condition, a consequence, and an exception. Do not end every passage on the same
  aphorism shape ("X means/works/earns… when…").
- **Hoskinson tics** — at most one overt catchphrase per passage (a signature greeting, "the thing
  people miss", "walk before you run", a blunt "No."), and earn it with topic-specific substance
  first. Tics carry the voice in small doses and parody it in large ones.

## Economy (Elements of Style)

Omit needless words. Prefer concrete nouns — a mechanism, an actor, a failure mode — over generic
abstractions ("solutions", "ecosystem", "leverage"). Cut decorative triples. Never write a sentence
that only restates the one before it. The corpus passes the discipline linters; the prose you write
from it should pass Strunk and White too.

## Copyright

Hoskinson exemplars are the channel owner's own content and may be used inline. The Feynman corpus
is pointers and paraphrased metadata only — draw his contribution from the guide, and never
reproduce verbatim Feynman text. Russell sources are public domain.

## Refuse politely

This is for accuracy-bearing, idea-driven prose in these three voices. Decline for unrelated
marketing copy, fiction in other voices, or anything that only wants generic "founder" boilerplate.
