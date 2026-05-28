# Longfellow Liveness Map

This guide names the prose-translatable techniques the liveness layer borrows from
Longfellow and a small tradition of poetic-but-disciplined prose (Carson, Dillard,
Eiseley). It mirrors `russell-corpus-map.md` in role: the positive moves the linters
cannot reward and the writer should reach for.

Anchor snippets are stored in `assets/longfellow-corpus/index.json` (public-domain,
verbatim, attributed). In-copyright prose models are referenced by named technique
only and never quoted.

The firewall: borrow cadence and image-logic only. Never the meter, rhyme, archaism,
or sentiment.

## The six techniques

### 1. Sentence-length percussion (Le Guin)

After a cluster of medium or long sentences, a short sentence — fewer than eight words
— marks arrival. The short sentence is amplified by what surrounds it; never produce
four consecutive sentences of similar length.

### 2. Cumulative, base-clause-first sentence (Christensen)

State the main claim first. Then add one to three free modifiers, each more specific
than the one before. Forward motion, not suspension. Default to cumulative; reserve
periodic (claim-last) for deliberate climactic weight.

### 3. Knot-and-resolution cadence (Stevenson)

At least once per substantive paragraph, build a sentence whose early clauses create a
tension and whose final clause resolves it — on the narrower, more specific term, not
a grand generalization. Subtle sound concordance is welcome; metrical regularity is not.

### 4. Anaphora tied to the argued term

When developing a concept across three or more consecutive sentences, open two of them
with the same word or phrase — the term under argument, not an atmospheric word. The
repetition marks stages of an argument; never decoration.

### 5. Specific-named catalog with chosen syndeton

When listing instances that support a claim, name them exactly: proper names, technical
names, exact quantities, dates. Three exact items outweigh six vague categories. End the
list with asyndeton (no final conjunction) for compression, or polysyndeton (and... and)
when you want the reader to feel the weight rather than the speed of accumulation.

### 6. Concrete anchor per abstraction (Strunk & White, Rule 16)

After each abstract claim, add one sentence that names the smallest specific physical
thing that instantiates it. Choose for precision, not beauty. One concrete detail,
exactly chosen, outweighs three atmospheric adjectives.

## Anchor catalogue

| ID | Technique | Prose translation |
| --- | --- | --- |
| `hiawatha-antithesis` | antithetical spatial parallelism | Two sentences with mirrored skeletons hold contrasting claims; the verb is repeated to mark the pulse. |
| `hiawatha-catalog` | specific-named enumeration with polysyndeton | Name the items exactly and let repeated "and" make the weight of the list felt. |
| `hiawatha-anaphora` | rhetorical-question opening with anaphora | Open with the question you are about to resolve, in the reader's voice; repeat the wh-word once to mark the structure. |
| `evangeline-primeval` | deictic anchor — name then particularize | State the claim concretely first; name the two specific instances that make it visible in the next sentence. |

## Disciplined-lyricism prose models (referenced by technique, not quoted)

Three prose stylists demonstrate the lively-but-not-purple register the blend targets.
Use their techniques; do not quote them.

- **Rachel Carson** — anaphoric accumulation with epistemic progression (a repeated
  modal "would" building to "should"); parataxis as register shift; point-of-view
  ("as the gulls saw") grounding elevated prose in a biological specific.
- **Annie Dillard** — recurring concrete image that evolves semantically across an
  essay, doing argumentative work by accumulating contradictions; phonemic patterning
  (alliteration / assonance) that enacts the claim rather than ornaments it.
- **Loren Eiseley** — scale-collision: a human-scale physical particular juxtaposed
  with a geological or cosmological claim in one sentence, the collision doing the
  emotional work.

## The firewall (what each liveness anchor must not import)

Stop and rewrite if the prose has acquired any of:

- Two evaluative adjectives modifying the same noun.
- An adverb attached to a verb that already contains the adverb's meaning.
- An emotion word applied directly without a concrete vehicle for it.
- Any apostrophe — to the reader, to a personified abstraction, to nature.
- A word chosen because it is grander than the plain alternative.
- A clause where nature's condition mirrors the argument's emotional register.
- Metrical regularity audible when the sentence is read aloud.
- An image whose argumentative function cannot be stated in one sentence.

These are what `lint_ornament` flags, advisory in v1.

## Sources

In-repo:
- Russell vitality companion: `references/russellian-vitality-guide.md`.
- Russell corpus anchors: `references/russell-corpus-map.md`.

External:
- Le Guin, *Steering the Craft* (sentence-length percussion).
- Christensen, *Generative Rhetoric of the Sentence* (cumulative construction).
- Stevenson, *On Some Technical Elements of Style in Literature* (knot-and-resolution).
- Strunk & White, *The Elements of Style*, Rule 16 (concreteness).
- Grabe & Low (2002), normalized Pairwise Variability Index (nPVI).
