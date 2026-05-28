# Design — add-voice-anti-monotony (revised after QA pass)

Full design: `docs/specs/2026-05-28-voice-anti-monotony-design.md`. This file records
the technical approach and the decisions the QA pass forced.

## Approach

Extend the existing `VOICE` capability with three instruments — two rebuilt
deterministic linters and one LLM-judge — plus a corpus expansion (two new donors)
and a validation plan with preregistered falsification. No new capability slug.

The three instruments form a stack:

- **`lint_chassis_uniformity`** — cheap deterministic pre-filter. Catches the obvious
  cases: marker-hit shape dominance over a 3-of-5 window, consecutive-shape streaks,
  low shape-sequence entropy, high humanity-token closer density. Pure stdlib.
- **`lint_humanity_token_closers`** — cheap deterministic pre-filter on closer shape.
  Pure stdlib regex.
- **`chassis_judge`** — top-of-stack LLM reader. Induces a per-paragraph move taxonomy
  per essay; reports most-frequent-move frequency and an unsympathetic critique.
  Caller-provided dispatcher (no live calls in code/tests; matches the reading-council
  pattern). The escape from the deterministic-instrument treadmill.

## Key decisions (and what the QA pass changed)

- **Rebuilt `lint_shape_variance` → `lint_chassis_uniformity`.** First draft
  proposed a single signal (5-of-6 window on `classify_paragraph`). QA found two
  failure modes: (i) `classify_paragraph` falls back to `assertion_justification` on
  any paragraph without explicit discourse markers, producing false-positive
  saturation on sparse-marker prose; (ii) the surface-shape vocabulary doesn't match
  the chassis fault (which lives one layer below the surface costume). The rebuilt
  linter combines four signals; the marker-hit requirement excludes the fallback;
  the closer-density signal catches chassis monotony even when surface shapes vary.
  Tightened the window from 5-of-6 to 3-of-5 — the original threshold was too lenient
  for the motivating case.
- **Renamed `lint_aphorism_density` → `lint_humanity_token_closers`.** QA verified
  the first-draft regex against every closer in the v1 snails essay and found it
  fires on **zero of nineteen**. The 18-word cap and the closed humanity-token list
  were the failure modes. Raised the cap to 28 (Russell's actual range), broadened
  the token list (added `men`, `man`, `nature`, `each of us`, indefinite-pronoun
  universals), added first-person-singular subtraction (grounding from Bendersky &
  Smith 2012 + AI2 GenericsKB filter rules). Renamed honestly: the instrument
  measures humanity-token-closer density, not aphorism density in the literary
  sense.
- **Added `chassis_judge` (LLM-judge step).** First draft dismissed this as "YAGNI-
  correct for a v1 advisory." The QA pass argued — correctly — that we are not on v1
  but on the third iteration of the same kind of fix, and deterministic regex is
  perpetually one abstraction-layer behind the reader. Adding the LLM-judge now
  prevents the next iteration from being yet another "ship the next regex" cycle.
  The judge follows the reading-council convention: dispatcher injected by caller,
  zero live calls in code or tests.
- **Dropped the self-turning paragraph mandate.** First draft mandated a self-
  turning paragraph in every essay with a guard "do not let the break itself become
  a template." QA found the construction self-contradictory ("must contain X" + "do
  not let X become a template"); the guard was unenforceable; the prescription was
  mechanically identical to the prior chassis prescription that produced the fault
  we're now treating. The donor expansion + LLM-judge carry the counter-monotony
  load.
- **Expanded the donor change from one entry (Didion) to two (Didion + McPhee).** QA
  argued that one un-quotable post-1950 donor against four pre-1960 quotable-or-
  Edwardian donors couldn't shift the register. Adding McPhee — orthogonal register
  (technical-essay process-as-argument) — gives the post-1950 side real weight.
- **Corrected the Didion entry substantively.** First draft called Didion "anti-
  aphoristic." QA research (Wilkinson 2025; Als 2020; Harrison 1980) confirmed the
  more accurate framing: Didion uses **aphorism as target, not as payoff** — opens
  with the generalising claim and dismantles it. Replaced the one-bullet sketch
  with a citation-backed 5-technique entry plus failure modes plus canonical texts.
- **Promoted `_strip_quotes` to public `strip_quotes`.** Unspecified reuse path in
  the first draft. Picked the one-line public-rename + cross-import option, matching
  the existing `from scripts.lint_paragraph_motion import classify_paragraph` idiom.
- **Preregistered two falsification conditions in the validation gate.** QA argued
  the first draft's "same-author writes v3.1 knowing the test" plan couldn't falsify
  the design. Preregistered: (1) `most_frequent_move_frequency ≥ 0.50` in v3.1 →
  fails; (2) `unsympathetic_critique` for v3.1 names the chassis → fails regardless
  of linter numbers.

## CI constraint

All three deterministic linters (`lint_chassis_uniformity`,
`lint_humanity_token_closers`, plus the existing `lint_ornament` it builds on) are
stdlib + `re` only. `chassis_judge` is stdlib + a caller-provided dispatcher (no
network in tests). All three new test files (`test_chassis_uniformity.py`,
`test_humanity_token_closers.py`, `test_chassis_judge.py`) take
`pytestmark = pytest.mark.windows_canary` and are named without the `test_lint_`
prefix so the russellian-style conftest's spaCy-absent `collect_ignore_glob` doesn't
silently skip them.

## Rejected

A new `voice-anti-monotony` capability slug (extend `VOICE`); a self-turning paragraph
mandate (self-contradictory); auto-wiring `chassis_judge` into `voice_eval`
(dispatcher dependency); promoting any linter to a hard gate (advisory in v1 per
convention); folding the new signals into the liveness composite (would worsen its
documented saturation); a third post-1950 donor (two is enough to put weight; more
dilutes per-donor signal).
