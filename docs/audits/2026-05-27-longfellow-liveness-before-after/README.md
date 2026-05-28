# Longfellow × Russell liveness blend: before / after — measured by the suite

Date: 2026-05-27

Two essays on the same subject ("The printing press and the limits of disruption") in
the russellian-style narrative-editorial mode. `baseline.md` uses the prompts at
`origin/main` (no liveness layer). `blended.md` uses the prompts on
`feat/longfellow-liveness` (the per-mode `## Liveness` layer at intensity *high*, anchored
in `assets/longfellow-corpus/index.json`).

The success gate for this change is **the reading council, not a deterministic score**:
flow and enjoyment must rise without quality falling. The voice_eval telemetry is
descriptive.

## Result

| metric | baseline | blended | reads as |
|---|---|---|---|
| Enjoyment | 3 | 4 | up |
| Flow | 3 | 4 | up |
| Style | 3 | 4 | up |
| Quality | 4 | 4 | flat (no regression) |
| Overall | 3.25 | 4.00 | up |
| Flesch | 53.81 | 56.38 | flat (plain) |
| burstiness | 0.546 | 0.694 | up (more varied) |
| nPVI cadence | 69.68 | 79.62 | up |
| ornament total | 0 | 0 | clean both sides — firewall held |
| liveness (composite) | 0.424 | 0.424 | flat (saturated — see note) |

## Reading

The change earns the gate. Flow and enjoyment lift one full point each on the 1–5
council scale; style lifts as well; quality stays at 4 — no regression on the
substance. The deterministic signal corroborates: **nPVI rises 9.94 points** (69.68 →
79.62), and **burstiness rises 0.148** (0.546 → 0.694), the two stdlib measurements
sensitive to ordering and sentence-length variation. The lift is the cadence shift the
liveness layer is engineered to produce: long sentences resolving on shorter ones, the
short sentences landing as verdicts.

The **ornament firewall held**: zero findings in both passages. Neither essay imports
archaism, apostrophe ("O Reader"), bare emotion words, adverb-amplified verbs,
nature-mirrors-mood, or adjective stacking. The Longfellow blend takes only the
cadence and image-logic the map prescribed; the meter, rhyme, and sentiment stayed
out.

The **composite liveness number is flat (0.424 / 0.424), and this is misleading by
construction.** Two of the four components are saturated or absent in this audit:

- *Cadence* is capped at 1.0 (the composite divides nPVI by 60 and clamps; both
  passages exceed 60, so both register 1.0 — the +9.94 nPVI delta is invisible to the
  composite).
- *Concreteness* is fixed at 0 because `lint_concrete_instance_density` requires the
  spaCy `en_core_web_sm` model, which is not installed on the audit host.

The genuine lift lives in the *raw* signals — nPVI, burstiness, and the reading
council — not in the rolled-up composite. This is the case for treating the composite
strictly as advisory telemetry, never as a verdict (REQ-VEVAL-012). On a host with
spaCy installed, and with the cadence band recalibrated above its current ceiling, the
composite would discriminate; here it does not.

## Honest caveats

- **Not a double-blind reader study.** Both passages were written by the same author,
  against the two prompt versions, and scored by a role-played five-persona council.
  This is the suite scoring its own output. The audit demonstrates that the
  instruments capture the predicted trade-off shape; it does not certify the prose as
  livelier in absolute terms. That certification needs a blind external panel.
- **Topic-specific lift.** The liveness layer's effect varies by topic. Printing
  history offered abundant concrete instances (Gutenberg, Fust, Erasmus, the
  Stationers' Company, the Plantin folios, the Books of Hours from Bruges) that the
  cumulative + catalogue techniques could anchor on. Topics without that texture would
  produce a smaller deterministic delta.
- **Composite calibration.** The cadence-ceiling saturation noted above is a
  calibration finding for the next iteration: `_CADENCE_DENOM = 60.0` is on the low
  side of the Grabe & Low band. Raising it to 80–100 would let the composite
  discriminate within the lively range. Filed as future work, not blocking the
  change.

Passages: `baseline.md`, `blended.md`. Raw scores: `scores.json`. Audited against
`feat/longfellow-liveness` after Task 7 (`acaf975`).
