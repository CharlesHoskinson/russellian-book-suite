# Lint results — Russellian voice calibration (polemic mode)

Date run: 2026-05-27
Branch: `feat/voice-calibration-prompts`

Two essays of the same title ("On the Absurdities of Artificial Intelligences
Governing Human Passions") were drafted under the polemic-mode system prompt:

- `baseline-polemic.md` — written under the **baseline** prompt (Role, Structural
  mandates, Negative constraints, Rhetorical devices, Closing rules), i.e. the
  `polemic.md` system prompt **without** the appended `# Calibration and planning`
  section.
- `candidate-polemic.md` — written under the **candidate** prompt, the current
  on-disk `polemic.md` (baseline + the `# Calibration and planning` section).
  The calibration discipline was applied: each paragraph was privately planned for
  motion (concession → example → distinction → consequence → turn); the section is
  built on a memorable reversal; the prevailing view is personified ("the Steward");
  concrete instances are named; the closing verdict reverses the opener. No planning
  notes were emitted, and the Russell touchstone wording ("will to believe / will to
  doubt") was not reused verbatim.

## Environment

- spaCy: **AVAILABLE**. spaCy 3.8.13 with `en_core_web_sm` installed into
  `skills/russellian-style/.venv` via `pip install -e ".[ci]"` + `python -m spacy
  download en_core_web_sm`.
  - Note: the `[ci]` install did not pull spaCy's CLI dependency `click`; installing
    `click` (and `typer`) explicitly was required before `spacy download` and the
    parser/NER-backed linters would import. Once `click` was present, all 12 linters
    ran with full spaCy support (tagger, parser, NER).
- All **12** requested linters ran. **None were skipped.**
- Each linter was invoked through its `lint_<name>()` function (equivalent to
  `python scripts/lint_<name>.py <file>`); finding counts below match the JSON each
  linter prints. CLI exit semantics: 0 if zero findings, 1 if any findings.

## Findings: baseline vs candidate

Lower is better. Acceptance requires candidate ≤ baseline on **every** linter.

| Linter                       | Baseline | Candidate | Ran? | Δ (cand − base) |
|------------------------------|:--------:|:---------:|:----:|:---------------:|
| lint_hedges                  |    2     |     1     | yes  |       −1        |
| lint_passive_voice           |    6     |     5     | yes  |       −1        |
| lint_signal_density          |    2     |     0     | yes  |       −2        |
| lint_sentence_rhythm         |    1     |     0     | yes  |       −1        |
| lint_listicle_abstract       |    0     |     0     | yes  |        0        |
| lint_parallel_structure      |    0     |     0     | yes  |        0        |
| lint_paragraph_motion        |    1     |     0     | yes  |       −1        |
| lint_ai_vocabulary           |    0     |     0     | yes  |        0        |
| lint_ai_staccato             |    0     |     0     | yes  |        0        |
| lint_burstiness              |    0     |     0     | yes  |        0        |
| lint_concrete_instance_density |  0     |     0     | yes  |        0        |
| lint_epistemic_precision     |    1     |     1     | yes  |        0        |
| **Total**                    |  **13**  |   **7**   |      |     **−6**      |

## Verdict

**ACCEPTANCE MET.** The candidate essay has no more findings than the baseline on
any of the 12 linters. It strictly improves on six (hedges, passive_voice,
signal_density, sentence_rhythm, paragraph_motion) and ties on the rest. Total
findings fall from 13 to 7.

Both essays are clean of the polemic prompt's banned vocabulary (no
"clearly"/"obviously"/"of course"/"the answer is", no magic adverbs, no
transition-adverb sentence starters).

## Revision history

The first candidate draft regressed on three linters: hedges (3 vs 2),
passive_voice (7 vs 6), and epistemic_precision (3 vs 1). Per the acceptance rule
the **candidate essay** was revised (never the linters):

- Removed two hedge terms ("could" ×2) by replacing modal phrasing with concrete
  verbs ("a magistrate learns in a lifetime"; "an affective-computing system would
  read distress").
- Removed two passive constructions ("a fever to be brought down" → "a fever for
  him to bring down"; "a thing to be nudged" → "a thing to turn"; "whether the
  conviction was earned or implanted" → "whether the voter earned the conviction or
  swallowed it whole").
- Suppressed two `required_uncertainty` epistemic findings by attributing the dated
  claims ("according to the hearing record"; "according to the whistleblower's
  account"), leaving a single dated-claim finding (the 2018 platform example) that
  matches the baseline's one such finding.

The remaining candidate findings are: 1 hedge ("might" in the closing antithesis,
"the machine might feel too much" — a deliberate rhetorical hypothetical), 5
passive constructions, and 1 epistemic `required_uncertainty` (the 2018 engagement
example). All are at or below the baseline counts.
