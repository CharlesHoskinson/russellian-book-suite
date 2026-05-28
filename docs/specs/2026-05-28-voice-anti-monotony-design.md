# Voice anti-monotony — design (revised after QA pass)

Date: 2026-05-28
Status: revised after research + red-team pass; awaiting plan
Change: `openspec/changes/add-voice-anti-monotony/`
Base branch: `feat/longfellow-liveness` (depends on the per-mode `## Liveness`
sections, `longfellow-liveness-map.md`, and `assets/longfellow-corpus/` from that
change).

## Problem

The Longfellow-liveness blend solved the decoration fault diagnosed in the v1 snails
essay. A v3 snails essay produced by the new voice was then read for its own faults,
and the reader's verdict landed cleanly: the voice has *one move and runs it sixteen
times* (fact → pivot → aphorism about humanity). The reader's ear learns the meter by
paragraph four. The piece performs wisdom on a metronome. The persona is too pleased
with itself. The diction is Edwardian-familiar-essay pastiche. The suite's instruments
(reading council, ornament linter, liveness composite) gave the essay 4/4/4/4 and
missed the structural fault entirely.

That gap — the suite cannot see what the reader sees — is the next iteration's target.

## What the QA pass changed

The first draft of this spec proposed two deterministic linters (`lint_shape_variance`,
`lint_aphorism_density`), a self-turning paragraph mandate in the mode prompts, and a
single new donor (Joan Didion). A five-agent QA pass — two adversarial red-teams and
three research dispatches — surfaced six findings that materially reshape the spec.
The findings, ordered by damage:

**1. The two proposed linters do not measure what they claim.** `lint_shape_variance`
operates on `classify_paragraph`'s surface shapes (`assertion_only`, `contrast`,
`concession_turn`, …), but the chassis fault sits underneath those shapes. The
fact-→-pivot-→-aphorism chassis wears any of the seven surface costumes, and
`classify_paragraph` falls back to `assertion_justification` on any paragraph without
explicit discourse markers — false-positive saturation on Didion-style prose.
`lint_aphorism_density`'s regex, hand-verified against every paragraph closer of the
v1 snails essay, fires on **zero of nineteen** closers: the 18-word cap eliminates
roughly half of Russell's characteristic closers (his aphorisms run 20–30 words), and
the closed humanity-token list misses "men/man," "nature," and abstract-noun
closures.

**2. The deterministic-linter strategy has hit its limit.** The pattern is: ship
liveness → reader finds decoration fault → ship anti-decoration linters → reader
finds chassis fault → ship anti-chassis linters. Regex matches `n+1`-gram patterns;
the reader catches the pattern of the patterns. The deterministic stack will always
be one level behind. Calling the LLM-judge step "YAGNI-correct for v1" was the wrong
reasoning at this point — we are not on v1; we are on the third iteration of the
same kind of fix.

**3. The first draft's Didion characterization was substantively wrong.** "Anti-
aphorism" misnames her core move. Critical consensus (Alissa Wilkinson, *We Tell
Ourselves Stories*, Liveright 2025; Hilton Als, *NYRB*, Dec 2020; Harrison 1980;
*Berkeley Fiction Review*, 2024) is that Didion uses **aphorism as target, not as
payoff**. "We tell ourselves stories in order to live" opens *The White Album* — and
the essay then spends fourteen fragments demonstrating that claim's instability. The
teachable distinction is *aphorism as arrival* (Russell, ending a paragraph) versus
*aphorism as target* (Didion, opening an essay to dismantle the opening). The richer,
citation-backed entry replaces the one-bullet sketch.

**4. The self-turning paragraph mandate is self-contradictory.** "Must contain X" +
"do not let X become a template" is a near-contradiction; "every essay contains a
self-turning paragraph" *is* a template by construction. The guard clause is
rhetorical, not enforceable, not measured by any linter. The mandate as prompt-level
prescription is mechanically identical to the prior chassis prescription that produced
the fault we are now treating. **Dropped from the revised spec.**

**5. One un-quotable post-1950 donor against four pre-1960 quotable-or-Edwardian
donors does not shift the register.** The donor change needs two post-1950 entries,
not one, to put real weight on the contemporary side of the corpus.

**6. The validation plan has no falsification condition.** Same-author writes
snails-v3.1 knowing the test; under those conditions the linter numbers cannot
falsify the design. Two falsification conditions preregistered in the revised spec.

The research dispatches also produced citable grounding: structural-monotony detection
literature (Coh-Metrix paragraph-SD, Swales-style move-sequence mining at ACM LAK 2017,
the Barzilay-Lapata entity-grid model, Browne & King's effect-repetition distinction,
the ProWritingAid Sentence Structure Report); aphorism/genericity detection literature
(Bendersky & Smith 2012; Danescu-Niculescu-Mizil et al. 2012 "You Had Me at Hello";
AI2's GenericsKB filter rules); and the corrected Didion craft analysis.

## Architecture

Extend the existing `VOICE` capability with **three** instruments (two rebuilt
deterministic linters + one new LLM-judge), a corpus expansion (two new donors), and
a validation plan with preregistered falsification. No new capability slug.

### Components

| File | New / Mod | Responsibility |
|---|---|---|
| `skills/russellian-style/scripts/lint_chassis_uniformity.py` | new | Rebuilt shape-variance linter. Combines four signals (see §3a). Pure stdlib. Reuses `classify_paragraph` from `lint_paragraph_motion` (stdlib). Returns `list[dict]`; advisory. |
| `skills/russellian-style/tests/test_chassis_uniformity.py` | new | Tests (filename not `test_lint_*`, marker `windows_canary`). Fixtures: a 6-paragraph monotone-marker-hit document flags; a 6-paragraph varied document does not; a fallback-dominated document (no markers) does **not** trigger the dominance check (the linter must distinguish marker-hit dominance from fallback saturation). |
| `skills/russellian-style/scripts/lint_humanity_token_closers.py` | new | Rebuilt aphorism linter, renamed honestly. Broadened humanity tokens (adds `men`, `man`, `nature`, `each of us`); raised word cap (28 words); first-person-singular subtraction (`\bI\b|\bmy\b` disqualifies); concrete-instance-marker disqualifier preserved. Quote-excluding via the shared `strip_quotes` helper (see §3c). One finding per qualifying closer. Pure stdlib regex. |
| `skills/russellian-style/tests/test_humanity_token_closers.py` | new | Tests (filename not `test_lint_*`, marker `windows_canary`). Fixtures include the v1 snails closers the first-draft regex missed (Russell-length aphorisms, "men"-generalisation, "nature"-subject, abstract-noun closer); plain-descriptive closers do not flag; first-person-singular sentences do not flag; quoted spans excluded. |
| `skills/russellian-style/scripts/chassis_judge.py` | new | **LLM-judge step.** Single LLM call per essay, caller-provided dispatcher (no live calls in tests, mirrors `reading_scores.run_reading_council`). Extracts per-paragraph rhetorical moves, induces a move taxonomy, reports most-frequent-move frequency, and emits a one-sentence "unsympathetic critique." Advisory. Returns `dict` (see §3b). |
| `skills/russellian-style/tests/test_chassis_judge.py` | new | Tests with a fake dispatcher: behavior is correct given a known response; prompt is well-formed; never makes a live LLM call. |
| `skills/russellian-style/scripts/lint_ornament.py` | mod | Rename module-private `_strip_quotes` to public `strip_quotes` (one-line rename). Existing call sites within `lint_ornament` updated. Module docstring noted as the canonical home of the quote-strip helper. |
| `skills/russellian-style/scripts/voice_eval.py` | mod | Add `chassis_uniformity` and `humanity_token_closers` to `_linters()`. The LLM-judge step is **not** wired into `voice_eval` (kept separate, like `reading_scores`, since it requires a dispatcher); audits invoke it directly. |
| `skills/russellian-style/references/longfellow-liveness-map.md` | mod | (a) Replace the first-draft Didion bullet with the corrected 5-technique entry (aphorism-as-target, catalogue-as-withheld-verdict, landscape-as-pre-argument, fragmentary-form-as-argument, physical-circumstance-as-epistemic-condition); failure modes; canonical texts; critical sources. (b) Add **John McPhee** as the second post-1950 donor: technical-essay register, process-as-argument, the long sentence built around a verbed-noun chain, the named-expert quoted in service of the geological/structural point. |
| `openspec/changes/add-voice-anti-monotony/tasks.md` | new | OpenSpec convention — implementation checklist with REQ-ID citations per task line. |
| `openspec/changes/add-voice-anti-monotony/specs/russellian-voice/spec.md` | new | Spec delta — `ADD REQ-VOICE-018..031` (14 REQs; numbering continues from `add-longfellow-liveness` at 017; no renumbering). |
| `docs/audits/2026-05-28-snails-v3-vs-v3.1/` | new | Validation artifact. snails-v3.1.md (rewritten + Lippinus/Bernoulli-mason fixes); chassis-judge.json (the LLM-judge output on both essays); deterministic-telemetry.json (the linter numbers); README.md (the comparison and the two preregistered falsification conditions, with their resolution). |

## §3 — Component specifics

### 3a. `lint_chassis_uniformity.py`

Pure stdlib, advisory. Combines four signals computed over the document; each emits
one or more findings independently, and the linter returns the union.

1. **Marker-hit shape dominance.** Slide a 5-paragraph window. For each window, count
   each shape *only* where `classify_paragraph` matched an explicit marker (i.e.,
   not the `assertion_justification` fallback for marker-less paragraphs). If any
   single marker-hit shape occupies ≥3 of 5 (60%), emit one finding. **Tightening
   the window from the first draft's 5-of-6 and excluding the fallback addresses the
   two false-positive failure modes the red-team identified.**

2. **Consecutive-shape streak.** Independent of (1), scan for runs of ≥3 consecutive
   paragraphs sharing a shape (any shape, including the fallback). Emit one finding
   per run.

3. **Paragraph-shape-sequence entropy.** Document-level signal. Compute Shannon
   entropy of the per-paragraph shape sequence (`H = -Σ p(s) log₂ p(s)`). Maximum
   entropy for the 7-shape taxonomy is `log₂(7) ≈ 2.81 bits`. If `H < 1.5 bits`
   (less than half maximum variety), emit one document-level finding. *Grounding:
   AI-homogenisation literature reports "cohesion architecture lost 70-78% of its
   variance" in AI-augmented essays; entropy is the direct measure.*

4. **Closer-density concentration.** For each paragraph, compute whether its closing
   sentence matches the humanity-token closer shape (reuses `lint_humanity_token_closers`).
   If ≥50% of paragraphs (with at least 8 paragraphs in the document) have a humanity-
   token closer, emit one document-level finding. *This catches the chassis when the
   surface shapes are varied but the closer-type repeats — the original red-team
   complaint.*

Each finding: `{"rule": "chassis-uniformity", "signal": <one of "marker_dominance"|"streak"|"entropy"|"closer_concentration">, "tier": "important"|"advisory", "severity": "advisory", "detail": {...}}`. `tier` is `important` for streaks ≥4, marker-dominance ≥4-of-5, entropy < 1.0, or closer-density ≥70%; otherwise `advisory`. Severity stays advisory.

Reuses `classify_paragraph` (stdlib) and `lint_humanity_token_closers` (the new sibling, also stdlib). No spaCy, nothing from `lint_common`.

### 3b. `chassis_judge.py`

The escape from the deterministic-instrument treadmill. One LLM call per essay,
caller-provided dispatcher (no live calls in code or tests; mirrors
`reading_scores.run_reading_council`).

Signature:

```python
def chassis_judge(doc_text: str, *, dispatcher: Callable[[str], str]) -> dict
```

The prompt asks the LLM to:
1. Read the essay and label the rhetorical move executed in each paragraph (induce
   the taxonomy; don't assume one).
2. Report the move taxonomy actually used.
3. Report the most-frequent move and its frequency (as a fraction of paragraphs).
4. State whether the essay can be summarised in a single move-shape (`yes` / `no`).
5. Write a one-sentence critique an unsympathetic reader would write.

Returned dict:

```python
{
    "metric": "chassis-judge",
    "paragraph_moves": list[str],      # one per paragraph
    "move_taxonomy": list[str],        # the unique moves induced
    "most_frequent_move": str,
    "most_frequent_move_frequency": float,  # 0..1
    "single_move_summary": bool,
    "unsympathetic_critique": str,
    "advisory": True,
}
```

Two parsing helpers ship alongside (`_build_judge_prompt`, `_parse_judge_response`),
both pure functions, both unit-testable without an LLM. The dispatcher is the only
side-effecting boundary.

The judge is **not** wired into `voice_eval._signals` — it requires a dispatcher and
the eval is meant to be runnable without one. Audits invoke `chassis_judge` directly,
alongside `voice_eval`, the way the prior audit invoked `reading_scores` alongside
`voice_eval`.

### 3c. `strip_quotes` rename (engineering fix)

`lint_ornament.py` currently has `_strip_quotes` as a module-private helper.
`lint_humanity_token_closers` needs the same logic. Three options were considered
(copy-paste / cross-import private / extract to shared module); the cleanest is the
one-line rename to public `strip_quotes` in `lint_ornament.py`, then cross-import:

```python
from scripts.lint_ornament import strip_quotes
```

This matches the established cross-import idiom (`voice_eval._motion_variety` already
does `from scripts.lint_paragraph_motion import classify_paragraph`). Module docstring
of `lint_ornament` annotated to record that it is the canonical home of the helper.

### 3d. `lint_humanity_token_closers.py` (rebuilt)

Pure stdlib regex. Per-paragraph: extract the closing sentence; apply gate; emit at
most one finding per paragraph if gate passes.

Closing-sentence gate (in order):

1. **Strip quotes** via `strip_quotes` (shared with ornament linter).
2. **Word count.** Must be between 6 and 28 words (raised cap from the first draft's 18; lowered floor to 6 since the v1 essay's "Slowness, well defended, is a kind of strength" is 8 words and was a clear false negative — calibration set to 6 so similar compact aphorisms are not missed).
3. **Humanity-generalising token present** (case-insensitive match against the broadened closed list):
   `we, our, us, ourselves, mankind, humanity, civilisation, modern life, most people, most of us, the rest of us, none of us, men, man, nature, the modern world, each of us, no one, anyone, everyone`.
4. **Concrete-instance marker absent.** No capitalised non-initial word (proxy for proper noun); no 4-digit year; no numeric quantity.
5. **First-person singular absent.** No `\bI\b` and no `\bmy\b`. Real aphorisms generalise; first-person-singular closers are testimony, not aphorism. (Per Bendersky & Smith 2012 and the GenericsKB filter rules: personal deictic anchors disqualify generic statements.)

If all five gates pass, emit one finding:

```python
{
    "rule": "humanity-token-closer",
    "paragraph_index": int,
    "closer": str,
    "tier": "advisory",
    "severity": "advisory",
}
```

`voice_eval`'s standard `len(fn(path)) / n_words * 1000` then yields closers per
1000 words. Descriptive threshold (NOT a gate): **≥6 closers per 1000 words is the
fault Charles named** ("performs wisdom on a metronome"). Documented as calibration,
not encoded.

## §4 — The donor expansion (corrected and doubled)

Two new bullets in `longfellow-liveness-map.md`'s "Disciplined-lyricism prose models"
section.

### 4a. Joan Didion (corrected entry)

**Joan Didion** (1934–2021; works in copyright through at least 2047 — reference by
named technique only, never quote).

The core Didion move is not the aphorism but the aphorism's deferral. She accumulates
specific sensory and procedural detail — temperatures, brand names, route numbers,
furniture — until the reader is carrying an argument she has pointedly declined to
state. Five translatable mechanical moves:

1. **The diagnostic aphorism that eats itself.** "We tell ourselves stories in order
   to live" (*The White Album*, 1979) is not an inspirational declaration; it is a
   clinical diagnosis Didion spends the essay demonstrating to be unstable. The
   aphorism arrives as thesis; the essay dismantles it. In analytic prose: state the
   generalising claim early, then assemble evidence that complicates rather than
   confirms it; close without re-landing the opening statement.
2. **The catalogue as withheld verdict.** In "Some Dreamers of the Golden Dream"
   (*Slouching Towards Bethlehem*, 1968), the affair's mechanics — falsified motel
   registrations, lunch dates, remembered phrases — are listed without editorial
   comment. The accumulation *is* the judgment.
3. **The landscape that pre-argues.** "Some Dreamers" opens with the San Bernardino
   Valley as "a place where it is routine to misplace the future" before any human
   character appears. The setting states the conclusion in displaced form.
4. **The fragmentary form as argument.** *Slouching*'s title essay uses only two
   explicit transitional markers across 44 pages (documented in *Joan Didion:
   Slouching Toward Subtly Effective Transition*, 2017). White-space segmentation
   mirrors the "centre cannot hold" argument structurally.
5. **The physical circumstance as epistemic condition.** "On Morality" is written at
   119°F in the Enterprise Motel and Trailer Park in Death Valley; the physical
   conditions force the particular. The constraint on knowing licenses the
   observation that follows it.

**Failure modes** (Didionesque mannerism, to avoid): when repetition accumulates
without variation in force, loop replaces liturgy (per the *Harvard Review* on *Blue
Nights*); when "we" assumes a civilisational position the reader hasn't consented to,
detachment becomes superiority (Harrison 1980; Bellot *Lit Hub* 2020); when
juxtaposition connects nothing discoverable, it becomes surface shock.

*Canonical texts*: "Slouching Towards Bethlehem" (1968); "Some Dreamers of the Golden
Dream" (1968); "Holy Water" (1979); "The White Album" (1979); "On Morality" (1968);
"Why I Write" (NYT, 1976). *Critical sources*: Als, *NYRB* (Dec 2020); Harrison
(1980); Wilkinson, *We Tell Ourselves Stories* (Liveright, 2025); Bellot, *Lit Hub*
(2020); Berkeley Fiction Review (2024); Literary Arts Portland (2016).

### 4b. John McPhee (second post-1950 donor)

**John McPhee** (b. 1931; *New Yorker* essays 1965–present; works in copyright —
reference by named technique only, never quote).

McPhee's gift is the technical/process essay that makes geology, freight, oranges, or
basketball coaches read as argument. He counters the Edwardian-familiar-essay register
on a different axis from Didion: where Didion withholds the verdict, McPhee makes the
*process* the verdict. Three translatable moves:

1. **The long sentence as a chain of verbed nouns.** McPhee's signature is a
   cumulative sentence whose engine is a series of concrete verbs, each acting on a
   specific named noun: "The truck shifted, the load settled, the tarp belled." The
   sentence carries information density without ornament.
2. **The named expert as locus of the technical claim.** Rather than asserting a
   geological or institutional fact in the writer's voice, McPhee credits it to a
   specific named source ("Anita Harris, of the U.S. Geological Survey, told me…").
   This is the opposite of the abstract humanity-generalising closer — it is
   specificity-as-authority.
3. **The structural conceit borrowed from the subject.** *Annals of the Former World*
   uses geological time as its own structuring principle; *Oranges* tells its history
   in concentric layers like the fruit. The form mirrors the content's logic, without
   the form having to be stated.

**Failure modes**: when the named-expert technique becomes "as X told me" in every
paragraph, attribution itself becomes a tic; when the technical inventory accumulates
without ever pivoting, the essay turns into a Wikipedia article with a byline.

*Canonical texts*: *Oranges* (1967); *Coming into the Country* (1977); *Annals of the
Former World* (1998); "The Search for Marvin Gardens" (1972); "Travels in Georgia"
(1973). *Critical sources*: Sims, ed., *The Literary Journalists* (1984); Kerrane &
Yagoda, eds., *The Art of Fact* (1997); McPhee's own *Draft No. 4* (2017).

### 4c. The five-donor balance

With the corrected Didion entry and McPhee added, the disciplined-lyricism section
holds: Carson (anaphoric accumulation, pre-1960), Dillard (image-evolution, 1970s+
but consciously archaic), Eiseley (scale-collision, pre-1960), **Didion** (aphorism-
as-target, post-1950), **McPhee** (process-as-argument, post-1950). Two post-1950
donors with different registers (refusal + technical) meaningfully shift the corpus
weight off the Edwardian-familiar-essay register that produced the v3 pastiche
charge.

## §5 — What the spec *removes* from the first draft

- **The self-turning paragraph mandate.** Dropped. The mandate was self-contradictory
  ("must contain X" + "do not let X become a template"), the guard was unenforceable,
  and the prescription was mechanically identical to the prior chassis prescription
  it was meant to fix. The donor expansion and the LLM-judge step are the load-bearing
  counter-monotony interventions; a prompt-level mandate would just produce the next
  named fault.
- **`lint_shape_variance` as a single-signal linter.** Replaced by `lint_chassis_
  uniformity` (four signals, including the closer-concentration check that catches
  the chassis when surface shapes vary).
- **`lint_aphorism_density` as named.** Renamed to `lint_humanity_token_closers` so
  the instrument doesn't oversell what it measures. The detector now has plausible
  recall on the v1 snails essay's known-bad closers.
- **The single-donor Didion change.** Replaced by the corrected-Didion + McPhee
  two-donor change.

## §6 — Validation gate (with preregistered falsification)

The success artifact is **snails-v3.1**: a rewritten snails essay applying the
corrected design, fixing the two factual errors caught in the v3 critique (`Lippinus`
not `Hirpinus`; the Bernoulli stonemason carved an Archimedean spiral instead of the
requested logarithmic one).

The audit bundle compares v3 vs v3.1 by:

- **The two new deterministic linters.** v3 should produce ≥1 `chassis-uniformity`
  finding (specifically the `closer_concentration` signal) and ≥6/1000
  humanity-token-closers density; v3.1 should reduce both substantially.
- **The chassis-judge LLM step.** Both essays scored by `chassis_judge` with the same
  dispatcher and prompt; the resulting `most_frequent_move_frequency` and
  `unsympathetic_critique` reported side-by-side.
- **The reading council.** Same role-played five-persona protocol, blind ordering.

### §6a. Preregistered falsification conditions

The design fails if **either** of these conditions holds in the v3.1 audit:

1. **`chassis_judge.most_frequent_move_frequency` ≥ 0.50 in v3.1.** Half or more of
   the paragraphs executing one move-shape is the chassis fault by the LLM-judge's
   own taxonomy; if it holds, the design did not break the metronome.
2. **The unsympathetic-critique field of `chassis_judge` for v3.1 contains any of
   the strings**: `"chassis"`, `"template"`, `"metronome"`, `"one move"`, `"same
   move"`, `"every paragraph"`, `"sixteen times"` (or v3.1's count), or any
   substring matching `r"\b(perform|performing)\b.{0,20}\b(wisdom|insight|moral)\b"`.
   The LLM-judge naming the fault in v3.1 is the design's failure regardless of the
   deterministic numbers.

Either condition triggering means the design did not work. The audit must record the
outcome honestly, including in the failure case. There is no condition under which
"the linter numbers moved" is sufficient to declare success without the LLM-judge
also clearing.

### §6b. Honest caveats (carried from the prior audit)

Same-author non-blind rewrite. The suite scoring its own output. What the
instruments do and do not measure — explicit disclosure.

## §7 — Isolation, conventions, branch base

- Work in the git worktree at
  `~/.config/superpowers/worktrees/russellian-book-suite/feat-voice-anti-monotony`,
  on `feat/voice-anti-monotony` based on `feat/longfellow-liveness`.
- The parallel agent's checkout (`russell-pass-agentic-civ` in the main repo) stays
  untouched.
- PR base at finish time: `feat/longfellow-liveness` (stacked PR) until that branch
  merges to main, then rebase onto main. If `feat/longfellow-liveness` receives
  review feedback that alters the `## Liveness` subsections, the
  `longfellow-liveness-map.md` prose-models section, or `test_system_prompt_liveness.py`,
  this branch rebases after the parent merges; the donor additions and the linter
  work are independent enough to reapply by hand.
- OpenSpec change `add-voice-anti-monotony`; spec deltas continue REQ numbering at
  `REQ-VOICE-018` (no renumbering).
- All three new test files (`test_chassis_uniformity.py`,
  `test_humanity_token_closers.py`, `test_chassis_judge.py`) take
  `pytestmark = pytest.mark.windows_canary`, matching the existing convention. None
  are named `test_lint_*` so the conftest's spaCy-absent skip glob doesn't catch them.
- Terse commits, no AI attribution. TDD per task. New code stays import-safe under
  the CI `[ci]` extra (no top-level spaCy in the new deterministic linters; the
  chassis-judge tests stub the dispatcher).

## §8 — Rejected / deferred

- **Promoting any new linter to a hard gate.** Advisory in v1 by convention.
- **Folding the LLM-judge into `voice_eval`.** The judge requires a dispatcher; the
  eval is meant to be runnable without one. Kept separate (matches `reading_scores`).
- **Auto-running the LLM-judge in CI.** Network-using; left for orchestrator audit
  invocation only, like the reading council.
- **A new capability slug.** Extend `VOICE`; the prior iteration's red-team principle
  still holds.
- **A move-classifier trained on a labelled essay corpus.** Out of scope for this
  change; the LLM-judge induces its own taxonomy per-essay, which is the practical
  YAGNI choice.
- **A third post-1950 donor.** Two (Didion + McPhee) is enough to put real weight on
  the contemporary side; adding more dilutes the per-donor signal.

## §9 — Sources

In-repo:
- `references/russellian-vitality-guide.md`; `references/longfellow-liveness-map.md`
- `scripts/lint_paragraph_motion.py` (`classify_paragraph`), `lint_ornament.py`
  (`_strip_quotes` → renamed `strip_quotes`), `voice_eval.py`,
  `scripts/score_russell_delta.py`, `reading_scores.py` (the dispatcher pattern)
- `docs/audits/2026-05-27-snails-before-after/` (v1, v2); the v3 essay (this session)
- The v3 critique itself (this session)

External, deterministic-linter grounding:
- Coh-Metrix: Graesser, McNamara et al., *Automated Evaluation of Text and Discourse
  with Coh-Metrix* (Cambridge, 2014)
- Barzilay & Lapata, "Modeling Local Coherence: An Entity-Based Approach,"
  *Computational Linguistics* 34(1), 2008
- Swales-style move-sequence mining: ACM LAK 2017, "Towards mining sequences and
  dispersion of rhetorical moves"
- Browne & King, *Self-Editing for Fiction Writers*, Ch. 10 "Once Is Usually Enough"
- ProWritingAid Sentence Structure Report (commercial precedent for sentence-start
  variance)
- AI-homogenisation entropy literature: arXiv 2603.21228
- Structural-diversity framing: arXiv 2408.06186

External, aphorism/genericity-linter grounding:
- Bendersky & Smith, "A Dictionary of Wisdom and Wit," ACL 2012
- Danescu-Niculescu-Mizil et al., "You Had Me at Hello," ACL 2012
- AI2 GenericsKB: arXiv 2005.00660 (the filter-rule set our gate mirrors)
- Strunk & White, Rule 16 (concreteness as inverse of generality)
- Kahneman, peak-end rule (paragraph-closing position grounding)

External, donor entries:
- Didion: Als (NYRB Dec 2020); Harrison (1980); Wilkinson, *We Tell Ourselves
  Stories* (Liveright 2025); Bellot, *Lit Hub* (2020); Berkeley Fiction Review (2024)
- McPhee: Sims, *The Literary Journalists* (1984); Kerrane & Yagoda, *The Art of
  Fact* (1997); McPhee, *Draft No. 4* (2017)
