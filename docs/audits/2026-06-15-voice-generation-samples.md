# Voice generation samples — generated from the committed Hoskinson corpus

Topic (held constant): *Why formal verification belongs at the base layer of a blockchain.*
Chosen because it sits where all three voices have something to say.

These are **hand-authored against the corpus and guide**, not the output of an automated
generator. The pipeline (`tools/build-voice-corpus`) builds the corpus; it does not yet
generate prose. Each passage draws on the rhetorical moves tagged in
`skills/russellian-style/assets/hoskinson-corpus/index.json` and the cadence in
`skills/russellian-style/assets/hoskinson-corpus/transcripts/*.md` (signature open,
"the thing people miss", systems-tradeoff framing, change-without-consent-erodes-trust,
walk-before-you-run, candor, direct address), plus the Feynman/Russell contributions
from `references/triadic-voice-guide.md`. An automated generator now exists at `tools/build-voice-corpus/scripts/generate.py` (`python -m scripts.generate --topic ... --mode hoskinson|triadic`); it builds this same corpus-grounded prompt and calls the wired Anthropic llm_call. The samples above were authored before that wiring landed.

---

## Sample A — pure Hoskinson voice

Hey everybody, Charles Hoskinson here, broadcasting from warm sunny Colorado — always
warm, always sunny, sometimes Colorado. Today I want to talk about why we bet the whole
company on formal verification, because I get asked this constantly, and frankly a lot of
the criticism comes from people who've never shipped a line of provably-correct code in
their lives. Here's the thing people miss. When you write a smart contract you're not
writing an app, you're writing a law that runs on other people's money, and once it's
deployed you can't quietly patch it without hurting trust. So how do you solve that? You
prove it's correct before it ever touches a single ada. This isn't academic
navel-gazing. These are old ideas, very well understood in the academic community — we
didn't invent them, we just had the discipline to actually use them, and to publish the
proofs so there's nothing up the sleeve. And yeah, it's slower. Walk before you run. But
when you're building a world financial operating system, slow and right beats fast and
wrong every single time.

---

## Sample B — triadic fusion (Hoskinson open → Feynman develop → Russell close)

Look, let me tell you why formal verification isn't optional — and I'll show you, not just
assert it. Imagine you and I are settling a bet. With an ordinary contract we hand the
money to a referee and hope he's honest; a smart contract removes the referee, so the
rules themselves hold the money and release it only when the agreed condition comes true.
But now everything rides on those rules being exactly right, and "exactly right" is harder
than it sounds. Think of it the way you'd check arithmetic: you don't believe 27 times 453
because someone tells you the answer — you rederive it and watch the result fall out.
Formal verification does that for code. It rederives the program's behavior from its
specification, step by step, until correctness is forced rather than hoped for. So the
whole matter reduces to one sentence. A contract you cannot prove correct is a contract
you cannot trust with money. Everything else is commentary.

---

## Single-voice controls (for triangulation)

**Russell control:** A smart contract is a rule that disposes of value. A rule that
disposes of value must be exact. An inexact rule disposes of value wrongly. Therefore a
smart contract must be proven exact before it is used. Verification is that proof. Without
it, the contract is not trustworthy; with it, the contract is.

**Feynman control:** Suppose you and a friend make a bet on a coin flip, and instead of
trusting each other you write the rule on a piece of paper that pays out by itself. Lovely
— except the paper does exactly what it says, not what you meant. So you'd want to check,
before any money is on it, that what it says and what you meant are the same thing. That
checking, done with real rigor instead of a hopeful read-through, is what formal
verification is.

**Hoskinson control:** People love to dunk on us for being slow. You know what? You never
ship a financial system in a hurry. We could've copy-pasted somebody else's virtual
machine and shipped in a weekend, and you'd be reading about the hack right now. Instead we
proved the thing works. That's not dogma, that's just respecting the fact that this is
other people's money. Walk before you run.
