# Before/After Examples

Six worked rewrites, showing Russellized prose transformed by a Feynman pass. Each example names the move(s) applied and confirms the argument is unchanged.

In all cases: the claims, logical order, and accuracy of the BEFORE are preserved in the AFTER. The Feynman pass works on the surface only.

---

## Example 1 — Memoization

**BEFORE (Russellized):**
> The function memoizes results; a repeated call returns the cached value, eliminating redundant computation.

**AFTER (Feynman):**
> The first time you ask, it does the work and tucks the answer in its pocket. Ask again, and it just hands you what's in the pocket — no work at all.

**Moves applied:** direct-address, plain restatement via physical picture (pocket).
**Argument unchanged:** same claim — first call computes, subsequent calls return cache.

---

## Example 2 — Renormalization

**BEFORE (Russellized):**
> The renormalization procedure removes divergences by absorbing infinities into redefined physical constants, though the mathematical justification remains contested.

**AFTER (Feynman):**
> Here is what we actually do: we get an infinite answer, we sweep it under the rug by redefining our constants, and we get a finite answer that matches experiment beautifully. Should that bother you? Yes. Does it stop us? No.

**Moves applied:** honest-doubt (surface the puzzle openly), direct-address ("should that bother you?").
**Argument unchanged:** same claim — renormalization works empirically; mathematical foundations are not fully settled.

---

## Example 3 — Entropy

**BEFORE (Russellized):**
> Entropy measures the number of microstates compatible with a given macrostate; higher entropy corresponds to greater configurational degeneracy.

**AFTER (Feynman):**
> Imagine a deck of cards sorted ace to king, suit by suit. Shuffle it once and you almost certainly get a mess. There are millions of mess-arrangements and only one tidy one. Entropy is just counting: most ways to arrange things look like a mess.

**Moves applied:** analogy (sorted deck as macrostate, shuffled arrangements as microstates), plain restatement ("just counting").
**Argument unchanged:** same claim — entropy counts compatible microstates; higher entropy means more configurations reach that macrostate.

---

## Example 4 — Hash function cost

**BEFORE (Russellized):**
> Computational overhead is incurred upon each invocation of the hash function. In performance-sensitive contexts, the frequency of execution requires evaluation.

**AFTER (Feynman):**
> Every time you call the hash function, you pay a small cost. If you're calling it a million times a second, that adds up. So before you scatter it through a hot loop, think about how often you actually need it.

**Moves applied:** direct-address ("you pay," "you're calling"), plain diction ("pay a small cost" replaces "computational overhead is incurred"), plain restatement.
**Argument unchanged:** same claim — per-call cost accumulates; evaluate call frequency in hot paths.

---

## Example 5 — Conservation laws as constraints

**BEFORE (Russellized):**
> Conservation laws constrain which physical transitions are permissible. A transition violating a conservation law does not occur, regardless of other conditions.

**AFTER (Feynman):**
> Nature has rules it simply will not break. Energy doesn't disappear; charge doesn't appear from nowhere. Whatever else is going on, if a proposed transition would violate one of these rules, it won't happen. Full stop.

**Moves applied:** plain restatement ("rules it will not break" for "constraints"), direct-address cadence, plain-diction ("full stop" deflates the stiff "regardless of other conditions").
**Argument unchanged:** same claim — conservation laws are absolute constraints on transitions; no exceptions.

---

## Example 6 — Consensus latency

**BEFORE (Russellized):**
> Achieving consensus in a distributed system requires that a quorum of nodes exchange messages until agreement on the committed value is established. Network latency bounds the minimum time to finality.

**AFTER (Feynman):**
> To agree on anything, the nodes have to talk to each other — and talking takes time. You can't get faster than however long a message takes to cross the network. That's your floor. Everything above that floor is protocol design; the floor itself is physics.

**Moves applied:** analogy (message crossing the network as a physical floor), plain restatement ("talk to each other" for "exchange messages"), direct-address ("your floor"), curiosity framing (distinguishes protocol design from physical bound).
**Argument unchanged:** same claim — quorum exchange required; network latency sets a lower bound on finality time.

---

## A note on the synthetic corpus entries

Examples 1–3 above expand the synthetic pairs from `assets/feynman-corpus/index.json` (`synthetic-001`, `synthetic-002`, `synthetic-003`). Examples 4–6 are original to this file. All six follow the same discipline: the AFTER is measurably warmer and more concrete; the logical content is byte-for-byte equivalent.
