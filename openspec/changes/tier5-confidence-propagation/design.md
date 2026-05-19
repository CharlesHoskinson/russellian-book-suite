# Design: tier5-confidence-propagation

## Weakest-link rule for defect confidence

Given a defect whose unsat core is the set of claim ids `C =
{c1, c2, ..., cn}`, the defect's confidence is
`min(:confidence c) for c in C`. The justification: a chain of
evidence is only as confident as its weakest link. A defect that
combines a `:confidence 0.95` regulatory claim with a `:confidence
0.4` extraction-noise claim is fundamentally as shaky as the 0.4
input; reporting the average would dilute the signal.

The min rule is also operationally cheap (one pass over the core)
and order-invariant, so the same core under different solver runs
produces the same confidence.

## Geometric mean for verdict-level confidence

Given a verdict with N defects, each carrying `:defect-confidence
d_i`, the verdict-level `:verdict-confidence` is
`(d_1 * d_2 * ... * d_N) ^ (1/N)`. The geometric mean penalises
low-confidence defects more aggressively than the arithmetic mean
would — one defect at `0.1` drags the verdict's confidence below
`0.5` even if every other defect is at `0.9`. That's the desired
behaviour: a verdict is only as trustworthy as its least-confident
defect.

If the verdict has zero defects, `:verdict-confidence` is `1.0`
(no evidence against the corpus, full confidence in cleanliness).

## Advisory-downgrade discipline

The threshold `VERIFIER_CONFIDENCE_THRESHOLD` (env var, default
`0.5`) sets the bar below which defects are reclassified. The
downgrade rule:

| chain confidence  | declared severity | rendered severity     |
|-------------------|-------------------|-----------------------|
| any atom >= T     | `:hard` / `:soft` | (unchanged)           |
| every atom < T    | `:hard` / `:soft` | `:advisory`           |

The downgrade fires when *every* atom in the core is below the
threshold — a single high-confidence anchor is enough to preserve
declared severity. The message the author sees attached to a
downgraded defect: `"all supporting claims have confidence below
{T}; this defect may be a false positive from extraction noise."`

The verdict JSON keeps the declared severity in
`:declared-severity` so consumers can recover it if needed; the
top-level `:severity` field reflects the rendered (post-downgrade)
severity.

## Ingest-time validation

`:confidence` is read at `ingest_ledger.py:167` today via
`claim.get("confidence", 0.0)`. The `0.0` default silently coerces
missing fields into "no confidence" without the author knowing.
Phase S replaces the default with a hard fail: a missing
`:confidence` raises `IngestConfidenceError("claim 'C042-...' has no :confidence field")`,
an out-of-range value raises
`IngestConfidenceError("claim 'C042-...' :confidence 1.4 out of range [0, 1]")`,
and a non-numeric value raises with the offending type. The error
type lives in the same module so import discipline matches existing
ingest errors.

## verdict_to_qa.py surfacing

The current QA JSON has a top-level `defects` array. Phase S adds
a parallel `advisory_defects` array; the renderer routes any
defect with `:severity :advisory` (post-downgrade) into the
advisory array rather than the main one. Authors see two banners:
the loud one for the high-confidence defects, the quiet one for
the advisory ones, distinguishable in book-qa's HTML output by CSS
class. The `:defect-confidence` and `:verdict-confidence` fields
flow through unchanged so book-qa can render them as percentages.

## Why not propagate uncertainty through the SMT solver itself?

A "probabilistic SMT" extension (Z3 has none) would let the solver
reason about claim confidence directly. We deliberately keep the
SMT pass pure-Boolean: the solver decides sat/unsat over the
atoms; the confidence layer is a post-hoc rendering on top of the
verdict. Two reasons. First, Z3's UNSAT cores are already
well-defined; replacing them with probabilistic cores would mean
re-validating decades of solver tooling. Second, the min-of-chain
rule is interpretable — an author can hand-trace it — while a
probabilistic solver's output would be opaque.
