# Before / After Examples

Ten paired transformations spanning common technical-writing failure modes. Use these as calibration when uncertain whether a passage is already compliant.

## 1 — Hedge removal

**Before:** The script might fail if the server is under heavy load.
**After:** The script fails when server CPU utilization exceeds 90 percent.

## 2 — Passive to active

**Before:** The configuration is loaded by the daemon at startup.
**After:** The daemon loads the configuration at startup.

## 3 — Adjective excision

**Before:** Our highly performant, extraordinarily reliable, enterprise-grade database engine.
**After:** The database engine handles 50,000 writes per second with 99.99 percent uptime.

## 4 — Conditional atomization

**Before:** Provided that authentication succeeds and rate limits are respected, and assuming the database is reachable, the request will be processed.
**After:**
1. Authentication succeeds.
2. Rate limits are respected.
3. The database is reachable.
4. THEN the request is processed.

## 5 — Code-as-illustration to code-as-proof

**Before:**
> Here is an example showing how to use the API:
> ```python
> client.fetch(id=42)
> ```
> As you can see, it is straightforward.

**After:**
> The `fetch` method retrieves a resource by primary key in O(log n).
> ```python
> client.fetch(id=42)
> ```
> The single positional argument forbids ambiguity between key types.

## 6 — Sideways drift removal

**Before:** Section 3 covers authentication. Authentication is interesting historically because early systems used plaintext passwords. Today we use OAuth2.
**After:** Section 3 covers authentication. The system uses OAuth2.

## 7 — Conversational closer removal

**Before:** I hope this helps you understand the architecture. Let me know if you have any questions!
**After:** *(deleted)*

## 8 — Nominalization to verb

**Before:** The implementation of the validation of the input is the responsibility of the parser.
**After:** The parser validates the input.

## 9 — Mixed list to parallel

**Before:**
- Install the package
- Configuration of the environment
- You should run the script
- Verification of outputs

**After:**
- Install the package.
- Configure the environment.
- Run the script.
- Verify the outputs.

## 10 — Speculation to threshold

**Before:** Performance is generally acceptable for most workloads.
**After:** P95 latency stays below 200ms for workloads under 10,000 requests per second.

---

## Anti-staccato contrast pairs

### Pair 1 — Bitcoin staccato → Russellian

**Bad** (linter-clean; AI-staccato):

> Speculation has obscured the philosophy. Many men bought Bitcoin not
> because they desired sound money, but because they desired more
> dollars. This is not a contradiction in the protocol. It is a
> contradiction in the buyer.

**Good** (analytic with motion):

> Those who call Bitcoin a mere speculation have seized upon a real
> defect and mistaken it for the whole subject. It is true that many
> men bought it in the hope of selling it to a more excited neighbour.
> But this tells us more about men than about the protocol. A system
> may be philosophically interesting even when most of its admirers
> understand it badly.

What changed: concession ("real defect"); distinction (men vs.
protocol); turn ("A system may be …").

### Pair 2 — Abstract-noun-subject overuse → Particular agents

**Bad** (subject `system` heads four consecutive sentences):

> The system records claims as data. The system projects those claims
> onto a graph. The system validates the graph against a SHACL shape.
> The system blocks the release when validation fails.

**Good** (particular agents):

> The author records claims as data; the system she works through
> projects each one onto a graph. A validator runs the SHACL pass, and
> the censor — for that is what a SHACL gate is — blocks the release
> when a constraint fails. The reader benefits because the chapter
> cannot ship with a quietly broken citation.

What changed: particular subjects (the author, the validator, the
censor, the reader); cadence variety; one sentence carries a
parenthetical aside that an abstract-subject run cannot.

### Pair 3 — "This is …" stacking → Consequence-carrying turn

**Bad** (three paragraph-final "This is …" / "It is …" sentences):

> Speculators bought the asset hoping the price would climb. This is
> not investment in any sober sense.
>
> Many buyers had no use for the asset beyond resale. This is a market
> for hope, not value.
>
> The protocol does not endorse this behaviour. It is a system, not a
> sermon.

**Good** (consequences that earn their last sentence):

> Speculators bought the asset hoping the price would climb. Their
> hope was not investment in any sober sense, but a wager on the next
> buyer's optimism.
>
> Many buyers had no use for the asset beyond resale. The market they
> joined was one of hope rather than value, and the distinction
> matters because hope is a poor anchor for a long-term holding.
>
> The protocol does not endorse this behaviour, nor does it forbid
> it. A protocol is a set of rules, not a sermon, and the rules say
> nothing about the wisdom of those who follow them.

What changed: each paragraph ends on a consequence ("a wager on the
next buyer's optimism", "a poor anchor for a long-term holding",
"the rules say nothing about the wisdom of those who follow them")
rather than a "This is …" identity claim. The paragraphs now depend
on each other; reordering them would lose the build.
