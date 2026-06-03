# Feynman Style Guide

This file catalogs the four moves that turn correct, dense Russellian prose into the kind of prose that clicks. Russell fixes the argument; Feynman warms the surface. The moves are not decorations — they are ways of helping a reader see what you actually mean.

Read this file when rewriting. Each move lists the principle, why it matters, and one tight before/after.

## Move 1 — Concrete analogy and physical intuition

Replace a bare abstraction with a tangible picture: an object you can touch, a scenario you can visualize, a number at a scale that makes sense. The analogy is not ornamental; it carries the logical content.

**Before:**
> Entropy measures the number of microstates compatible with a given macrostate; higher entropy corresponds to greater configurational degeneracy.

**After:**
> Imagine a deck of cards sorted ace to king, suit by suit. Shuffle it once and you almost certainly get a mess. There are millions of mess-arrangements and only one tidy one. Entropy is just counting: most ways to arrange things look like a mess.

The before-version is accurate and atomic. The after-version is also accurate and atomic, and now a reader can see it.

**Rule:** If you catch yourself writing "corresponds to," "is defined as," or "represents," ask whether a physical picture would carry the same logical content more directly.

## Move 2 — Conversational directness

Address the reader as "you." Use contractions. Ask the question the reader is already silently asking. Drop in an aside when it helps. A Russellian sentence like "one observes that…" is technically fine but keeps the reader at arm's length for no reason.

**Before:**
> The function memoizes results; a repeated call returns the cached value, eliminating redundant computation.

**After:**
> The first time you ask, it does the work and tucks the answer in its pocket. Ask again, and it just hands you what's in the pocket — no work at all.

The argument is identical. The second version lets the reader inhabit it.

**Rule:** If a paragraph never says "you" and never asks a question, read it aloud. If it sounds like someone is lecturing an empty room, add one "you" or one question.

## Move 3 — Curiosity and honest doubt

Surface the genuine puzzle before or alongside the solution. Admit when something is strange, when the answer is not fully satisfying, when you had to wave your hands. This is not vague hedging — it is exact intellectual honesty.

**Before:**
> The renormalization procedure removes divergences by absorbing infinities into redefined physical constants, though the mathematical justification remains contested.

**After:**
> Here is what we actually do: we get an infinite answer, we sweep it under the rug by redefining our constants, and we get a finite answer that matches experiment beautifully. Should that bother you? Yes. Does it stop us? No.

The second version says exactly the same thing about the contested status. It also says it in a way that makes the reader feel the tension rather than just note it.

**Rule:** When something is genuinely puzzling or unsettled, say so directly. "Should that bother you?" is not a hedge — it is precision about where the intellectual discomfort lives.

## Move 4 — Plain playful diction

Short Anglo-Saxon words over long Latinate ones. A touch of humor when the moment allows it. Deflate pomposity by naming the ordinary thing underneath the fancy name. Feynman called this "just plain talking."

**Before:**
> Computational overhead is incurred upon each invocation of the hash function, necessitating consideration of the frequency of execution in performance-sensitive contexts.

**After:**
> Every time you call the hash function, you pay a small cost. If you're calling it a million times a second, that adds up — so think about how often you actually need it.

The second version is shorter, clearer, and costs nothing in precision.

**Rule:** When you see "utilize," "commence," "necessitate," "invocation," or any word that would sound ridiculous if you said it out loud to a friend explaining this over lunch — replace it.

## The constraint beneath all four moves

None of the four moves may alter the argument. The claims, the logical order, the evidence — those belong to the Russell pass and are frozen. Feynman works on the surface only. If you find yourself softening a claim, adding uncertainty that was not already there, or reordering a point to feel more natural, stop — you have crossed from surface to argument.

`preserve_argument` enforces this as a hard gate. The four moves above operate strictly inside the boundary it draws.
