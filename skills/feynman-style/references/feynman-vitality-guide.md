# Feynman Vitality Guide

The negative linters catch what went wrong. This file covers what to do when the linters all pass but the prose still reads as flat, assembled, dutiful — correct but inert.

## The symptom

Plain vocabulary. No Latinate jargon. Sentences under 35 words. No AI slop. And yet reading it feels like watching someone explain a magic trick in a monotone. The argument is there; the life is not.

## The fixes

**1. Find the real puzzle and say it.**

Technical prose often buries the surprising thing under correct framing. Ask: what is actually strange about this? Where should a thoughtful reader stop and think "wait, how does that work?" Put that question on the surface. You don't have to resolve it immediately — naming it is the first move.

**2. Run a concrete example from start to finish.**

When abstraction accumulates across several paragraphs, pick one instance and follow it through every step — an actual function call, an actual molecule, an actual transaction. Not "for example, consider a node that…" as a gesture. Actually walk the reader through the instance until the abstract claim pays off in something tangible.

**3. Vary the cadence.**

Read the prose aloud. If every sentence ends with the same falling intonation, the same 15-to-25 word count, the same subject-verb-object shape — that is the problem. Mix short declarative sentences with longer ones that carry a qualification. A two-word sentence after four long ones wakes a reader up.

**4. Let honest doubt do real work.**

If there is something the argument does not settle, something still genuinely open, something you had to approximate — say so plainly and precisely. Not "further research is needed." Not a vague "while this approach has limitations." Something like: "This works for inputs under 10,000 entries; past that, nobody has benchmarked it seriously." That kind of honesty makes a reader trust everything else more.

**5. Address the reader once.**

Even one "you" or one "notice that" — used once in the right place, not scattered throughout — can reset the register from lecture to conversation.

## What not to do

Don't add analogies for their own sake. A thin analogy that doesn't carry the logical content is decoration, and decoration reads as padding. An analogy earns its place only if a reader who grasps it grasps the actual point.

Don't add rhetorical questions that you then immediately answer with a single word. "Why does this matter? Performance." is a tic, not a move.

Don't vary sentence length by hacking words off. Short sentences that drop necessary connectives are worse than long sentences that carry them.

## Check against the corpus

When vitality is missing, retrieve one or two entries from `assets/feynman-corpus/index.json` that match the rhetorical mode of the failing passage:

- Analogy missing → `quote-imagine-small`, `synthetic-003-after`
- Honest doubt missing → `quote-nobody-understands-qm`, `synthetic-002-after`
- Direct address missing → `quote-fool-yourself`, `synthetic-001-after`
- Plain restatement missing → `quote-jiggle`, `quote-disagrees-with-experiment`

The corpus entries are anchors, not templates. Use them to calibrate register and see what a live version of the move looks like.
