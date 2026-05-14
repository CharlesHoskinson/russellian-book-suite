# Russell Style Enhancement Research

Date: 2026-05-14

## Current Pull State

The local checkout at `C:\Users\charl\code\russellian-book-suite` is on `main` at `b72d8eb`, matching `origin/main`.

The repo copy of `skills/russellian-style` includes more than the installed skill copy under `C:\Users\charl\.agents\skills\russellian-style`. The repo copy adds sentence-rhythm and listicle-abstraction linters, and it reframes the skill as an audit system for hedges, passive voice, modifier bloat, parallel structure, rhythm, and listicle abstraction.

## Twenty-Paragraph Current-Skill Sample

Prompt used: Explain why a non-fiction drafting system needs a claim ledger.

1. A non-fiction drafting system needs a claim ledger because prose can sound exact while carrying false claims. The ledger gives every factual sentence an address.

2. A source enters the workspace as evidence, not decoration. The system records its origin, date, scope, and trust level.

3. A claim enters the ledger when the system can state it as a proposition. The proposition must identify its subject, predicate, object, and source.

4. The chapter contract selects claims from the ledger. The draft inherits those claims and must not invent replacements.

5. The writer can phrase a claim many ways. The ledger preserves the claim beneath the phrasing.

6. This separation matters because style changes faster than truth. A revision can improve a sentence without changing its evidential burden.

7. A claim without support has no right to enter the book. It can appear as a question, but not as a conclusion.

8. A disputed claim needs a rival claim. The ledger records the rivalry before the chapter resolves it.

9. A review panel cannot audit a mood. It can audit a claim, a source, and a transition between confidence states.

10. Confidence changes when new evidence enters the graph. The ledger records the old state, the new state, and the reason for the change.

11. This record prevents silent repair. A bad claim does not disappear; it becomes refuted, revised, or quarantined.

12. The reader benefits because the book stops pretending that fluency is proof. A smooth paragraph and a true paragraph are different objects.

13. The author benefits because the system turns doubt into work. It shows which proposition needs a source, a counter-claim, or deletion.

14. The editor benefits because the ledger makes revision local. A factual defect points to a claim identifier rather than a vague unease about a chapter.

15. The pipeline benefits because a machine can test a ledger. It cannot test confidence hidden inside eloquent prose.

16. The claim ledger also disciplines emphasis. Load-bearing claims receive more scrutiny than decorative facts.

17. This distinction keeps the system honest. An error in a caption matters; an error in the book's central inference matters more.

18. A release gate can therefore ask a precise question: which accepted claims still lack adequate support?

19. The answer becomes an engineering object. The system can block release, open a ticket, or request another source.

20. A book built this way remains revisable. Its sentences can change, but its obligations remain visible.

## Online Russell Reference Corpus

The following sources should seed the next corpus expansion. Public-domain Project Gutenberg texts can supply excerpts directly. The 1956 essay should be used only as a citation and short paraphrase unless licensing is clarified.

| Source | URL | Why It Matters For Style |
| --- | --- | --- |
| Bertrand Russell, *The Problems of Philosophy* (Project Gutenberg) | https://www.gutenberg.org/cache/epub/5827/pg5827-images.html | Shows Russell's general-reader exposition: question, distinction, concession, answer. The closing chapter mixes analytic structure with humane stakes. |
| Bertrand Russell, *Mysticism and Logic and Other Essays* (Project Gutenberg) | https://www.gutenberg.org/cache/epub/25447/pg25447-images.html | Shows Russell handling abstract opposition without flattening it. He contrasts mystic feeling with scientific discipline and lets both terms keep force. |
| Bertrand Russell, *Our Knowledge of the External World* (Project Gutenberg) | https://www.gutenberg.org/cache/epub/37090/pg37090-images.html | Shows the scientific-method voice behind logical atomism. It also shows wit, contrast, and argumentative pressure. |
| Bertrand Russell, *The Analysis of Mind* (Project Gutenberg) | https://www.gutenberg.org/cache/epub/2529/pg2529-images.html | Shows definition-by-progress. Russell starts from common terms, exposes their instability, then narrows the inquiry. |
| Bertrand Russell, *Free Thought and Official Propaganda* (Project Gutenberg) | https://www.gutenberg.org/cache/epub/44932/pg44932-images.html | Shows public argument. Russell uses sharp antithesis, political examples, and memorable inversions such as the wish to doubt. |
| Bertrand Russell, *Political Ideals* (Project Gutenberg) | https://www.gutenberg.org/cache/epub/4776/pg4776-images.html | Shows warmth without sentimentality. The prose keeps moral imagination alive while maintaining argumentative control. |
| Bertrand Russell, "How I Write" (1956 PDF copy found online) | https://www.stephenhicks.org/wp-content/uploads/2015/10/RussellB-How-I-Write-1956.pdf | Supplies Russell's explicit writing ideal: clarity in few words. It also shows that his method was not mere deletion; he cared about form only after meaning was right. |

## Comparison

The current sample passes the core spirit of the installed skill: it removes vague hedging, keeps actors visible, breaks complex claims apart, and avoids listicle abstraction inside the prose. It is easy to audit.

It does not yet sound like Russell. The sample has one dominant paragraph shape: a compact assertion followed by a compact justification. Russell often starts from an ordinary prejudice, grants it partial force, shows where it fails, and then turns the thought. The turn gives the prose life.

The current skill treats certainty as deletion of doubt. Russell treats uncertainty as an object of analysis. In the reference texts he distinguishes dogmatic certainty from rational doubt, and he frequently states the limits of his claim before tightening it.

The current skill removes ornament, which is correct. But Russell's life does not come from ornament. It comes from antithesis, dry wit, concrete names, historical examples, and human consequences. The sample says "the system" repeatedly; Russell would also give us the official, the censor, the philosopher, the ordinary man, the tired worker, or the student misled by practical prejudice.

The current skill makes each paragraph independent. Russell often makes each paragraph dependent on the last. His paragraphs do not merely accumulate propositions; they alter the reader's position.

The current linter suite measures many ways prose can fail, but it measures few ways prose can succeed. It can punish bloat, passivity, hedge terms, flat rhythm, and fake structure. It cannot reward a concrete instance, a useful concession, a witty antithesis, or a paragraph that earns its last sentence.

## Enhancement Plan

Skill packaging constraint: keep `SKILL.md` short and procedural. Put corpus notes, style doctrine, and calibration examples in one-level `references/` files; put machine-readable corpus metadata in `assets/`; put repeatable checks in `scripts/`. Do not add auxiliary README or changelog files inside the skill.

### Phase 1: Expand The Russell Corpus

Add `skills/russellian-style/references/russell-corpus-map.md`.

For each source, record title, year, URL, copyright status, rhetorical mode, recommended excerpt ranges, and style tags. Use at least four modes: analytic exposition, popular philosophy, public argument, and meta-writing.

Add `skills/russellian-style/assets/russell-corpus/index.json`.

Store metadata and short excerpt fingerprints. For public-domain Project Gutenberg texts, include excerpt ranges and small calibration snippets. For "How I Write", store citation metadata and paraphrased lessons only until licensing is clarified.

Status: implemented as a 50-paragraph public-domain corpus map, with source pointers and paraphrased style metadata rather than pasted source paragraphs.

### Phase 2: Add Positive Style Doctrine

Add `skills/russellian-style/references/russellian-vitality-guide.md`.

This guide should add positive rules that the current skill lacks:

- Begin with a human or intellectual difficulty, not an abstract system noun.
- Use concrete examples to earn abstractions.
- Permit explicit epistemic limits when they sharpen truth.
- Use antithesis to expose a distinction.
- Vary paragraph motion: common view, concession, distinction, consequence, turn.
- Let the last sentence of a paragraph change the pressure of the argument.
- Prefer dry irony over decoration when a false view deserves compression.

Revise `russellian-style-guide.md` so "no hedging" becomes "no vague hedging." Ban evasive uncertainty; allow exact uncertainty.

### Phase 3: Add New Linters And Metrics

Add `scripts/profile_russell_corpus.py`.

It should compute sentence-length distribution, paragraph-length distribution, first-word repetition, connective density, question rate, concrete named-entity rate, and concession-turn markers.

Add `scripts/lint_flat_axiom_stack.py`.

Flag runs where too many paragraphs share the same two-sentence assertion-plus-justification shape.

Add `scripts/lint_concrete_instance_density.py`.

Flag sections that make several abstract claims without a person, institution, object, place, date, or measurable event.

Add `scripts/lint_epistemic_precision.py`.

Replace the current hedge-only model with three categories: banned vague hedge, allowed bounded uncertainty, and required uncertainty where the evidence is incomplete.

Add `scripts/lint_paragraph_motion.py`.

Detect sections whose paragraphs only accumulate assertions and never use concession, question, contrast, example, or consequence.

### Phase 4: Replace Calibration Examples

Expand `references/before-after-examples.md` with paired examples for lifeless compliance.

Each pair should show:

- A linter-clean but dead paragraph.
- A Russell-aligned paragraph with the same facts.
- The specific motion that changed: concession, antithesis, concrete instance, or paragraph turn.

Add one 20-paragraph golden sample and one 20-paragraph anti-sample under `tests/fixtures/before_after/`.

### Phase 5: Evaluate Against Humans And Tests

Update `style_pass_report.py` to report both negative and positive metrics:

- `hedge_count`
- `passive_voice_ratio`
- `modifier_budget_violations`
- `rhythm_violations`
- `flat_axiom_stack_violations`
- `concrete_instance_density_violations`
- `epistemic_precision_violations`
- `paragraph_motion_score`

Add a `russell_vitality_score` for review use only. It should not block release until calibrated against at least three corpus sources and one real chapter.

Run the new skill against the current 20-paragraph sample, a Bermuda chapter, and one README section. Then send both old and new outputs through `book-review` with Gottlieb, Lay Reader, and AI-Slop Detector personas.

## Recommended Direction

The skill should stop treating Russell as maximal compression. Russell's better model is compressed movement: every sentence reduces ambiguity, but every paragraph also advances a living argument. The next version should keep the deterministic lint core and add a second layer that rewards concrete pressure, exact uncertainty, antithesis, and paragraph turns.
