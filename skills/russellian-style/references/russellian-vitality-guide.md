# Russellian Vitality Guide

The existing `russellian-style-guide.md` lists the negative rules: what to remove. This file lists the positive rules: what to put in. The deterministic linters can punish bloat, hedge, passive voice, listicle abstract, and flat rhythm; they cannot reward a concrete instance, a useful concession, a witty antithesis, or a paragraph that earns its last sentence. This guide tells the writer (human or agent) what those moves are.

The six rules below derive from the 50-paragraph corpus map at `references/russell-corpus-map.md`. Each rule cites one corpus entry that demonstrates it.

## 1. Open with a difficulty, not a system noun

Begin a paragraph with the human or intellectual difficulty the paragraph will address. Do not begin with "the system", "the framework", "the platform". A system noun in the subject slot tells the reader nothing has happened yet.

*Corpus exemplar:* `problems-006` ("Wrong conception split into two causes"). Russell opens by naming the wrong conception, not by describing the apparatus that produces it.

## 2. Use concrete examples to earn abstractions

Every abstract claim earns the right to exist by producing a concrete instance: a person, an institution, an object, a date, a measurable event, or one of the occupational nouns Russell relies on (the official, the censor, the philosopher, the worker).

*Corpus exemplar:* `problems-001` ("Relation made concrete through a room example"). Russell defines an abstract relation through an ordinary spatial case before naming it abstractly.

## 3. Permit exact uncertainty; ban vague hedging

Vague hedges (*perhaps*, *arguably*, *to some extent*) are evasive and banned. Exact uncertainty — *within 5%*, *under condition Y*, *in cases where the source has been verified* — is welcomed. Numeric specificity without a source attribution is itself a hedge; cite the source token.

*Corpus exemplar:* `mysticism-006` ("Ignorance stated plainly before the thesis"). Russell admits the limit of his knowledge before stating the testable claim.

## 4. Use antithesis to expose a distinction

When two positions are in tension, balance them in the same paragraph and let the contrast carry the point. Do not stage a list of positives followed by a list of negatives; that is a balance sheet, not an argument.

*Corpus exemplar:* `free-001` ("Belief opposed by rational doubt"). Russell builds the paragraph around a single memorable reversal: the wish to doubt set against the wish to believe.

## 5. Vary paragraph motion

A section that uses only assertion-and-justification paragraphs is a flat axiom stack. Russell varies motion paragraph by paragraph:

- common-view → concession → distinction → consequence → turn
- question → partial answer → new question
- ordinary case → instability under pressure → narrowed inquiry
- abstract claim → concrete counterexample → resulting refinement

*Corpus exemplar:* `analysis-001` ("Common examples open a technical definition"). The paragraph starts with what people think they know and then begins to make the term unstable.

## 6. Let the last sentence change pressure

The last sentence of a paragraph is its verdict, not its summary. It should leave the reader in a different epistemic position than the first sentence did. A paragraph that closes on a restatement of its topic sentence has wasted its second half.

*Corpus exemplar:* `problems-010` ("Uncertainty turned into value"). The paragraph ends with a reversal that changes how the reader values the limitation Russell has been describing.

## Using this guide alongside the negative rules

The negative-rules guide (`russellian-style-guide.md`) is enforced by deterministic linters. This guide is calibration material for the writer and the persona reviewers. The five new vitality linters (`lint_burstiness`, `lint_ai_vocabulary`, `lint_concrete_instance_density`, `lint_epistemic_precision`, `lint_paragraph_motion`) approximate the positive rules from the failure side: they detect the absence of these moves. They do not detect their presence; that judgment lives with the persona panel and the writer.

When a vitality linter fires, `style_pass_report.py` retrieves one corpus exemplar (via `retrieve_corpus_anchor.py`) whose rhetorical move corresponds to the missing motion. The exemplar is a reference + lesson, not a paragraph for the writer to imitate. Russell's value is the paragraph motion, not the diction.

## Calibrating to the delta band

When `score_russell_delta` reports prose at or past the edge of Russell's range, run
`score_russell_delta --diagnose <file>` to see *which* most-frequent words diverge.
A recurring pattern, observed across calibration work, distinguishes machine analytic
prose from Russell's:

- **Over-used: emphatic absolutes and bare anaphora.** "never", "cannot", "no",
  "nothing", "real", and a high rate of bare "it" and chained "and". These hammer.
  Russell asserts without insisting.
- **Under-used: subordinators.** "of" (the genitive "the X of Y"), "which" (relative
  clauses), "but" and "if" (concession and condition). These are the connective
  tissue of a balanced sentence.

So the calibration is not lexical surgery; it is the same vitality work. Replace an
emphatic absolute with a plain statement ("was never the binding constraint" →
"was not the binding constraint"); fold "X. It is Y." into "X, which …" (adds the
subordinator, drops the bare "it"); name a bare-"it" subject; break a run of "The …"
openings. Each move lowers the Delta *and* improves the prose.

Two warnings. First, **do not hunt single words.** The Delta is a distribution
distance; removing one *under-used* word (e.g. trimming "a handful **of** tools" to
"a few tools") can raise it. Edit for the move, then re-score. Second, the Delta is
**advisory**. Prose sitting at p90 is as Russellian as Russell's own 90th-percentile
paragraph; chasing the last thousandth is over-fitting a noisy metric and is exactly
the lexical hacking this guide exists to prevent. Stop when the prose is right.

## The negation-affirmation wall (the canonical machine tell)

The single most reliable sign of machine analytic prose is the negation-affirmation
template — "X is not Y. X is Z." / "This is not A. It is B." — stacked across
paragraphs. It passes every negative linter (no hedge, active voice, short sentences)
and still reads as a wall of compact assertions. `lint_ai_staccato` catches it.
The fix is a *move*, not a punctuation swap: a concession-turn, a distinction, or a
sentence that turns the argument rather than re-asserting it. Fold the pair into one
sentence with a real connective ("not a counterexample to the thesis **but** the case
it exists to worry about").
