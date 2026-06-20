---
name: voice-eval
description: "HFR v2 evaluation. Runs the 20×20 comparison between triadic-voice (v1) and triadic-voice-v2 (v2): generate in-session, gate on the russellian-style v1 floor, score the 8 liveliness signals, judge blind pairwise, monitor formula-drift, and report pass/fail. Use to decide whether v2 beats v1. The running model generates and judges; no API key."
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
---

# voice-eval

The HFR v2 acceptance test. Deterministic Python helpers do the bookkeeping and
statistics; **the running model does the generation and the judging in-session** (no
API key), exactly like `triadic-voice`/`triadic-voice-v2`. v1 is the frozen control.

## How to run the 20×20 (in-session)

1. **Load prompts.** `load_prompts()` → 20 prompts stratified 7/7/6.
2. **Generate both arms.** For each prompt, write one v1 passage (follow
   `triadic-voice/SKILL.md`) and one v2 passage (follow `triadic-voice-v2/SKILL.md`,
   using `build_generation_brief(topic, rotation)`). Feed these as the `generate_v1` /
   `generate_v2` callables to `run_arms(...)` → 40 passages.
3. **Gate on the v1 floor.** `gate_passages(passages, battery=default_battery)`. Any
   passage with violations is **regenerated** before scoring, so both arms are equally
   floor-clean (REQ-VEVAL-010).
4. **Signal deltas.** `compute_deltas(passages, scorer=default_scorer, signals=SIGNAL_NAMES)`
   (import `SIGNAL_NAMES` from the `liveliness-signals` skill_api — the 8 signal names)
   → per-signal mean delta v2−v1, overall and per register (REQ-VEVAL-011).
5. **Blind pairwise judge.** `build_ballots(v1_passages, v2_passages)` → 40 ballots
   (each pair judged in both orders, length-matched). For each ballot, judge blind:
   read A and B, give a chain-of-thought rationale, then fill the verdict
   (`keep`, `want_next`, and ordinal `momentum/clarity/voice_authority/readability/
   trustworthiness`). Never look at the arm labels. Aggregate with
   `win_rate(filled_ballots, target="v2")` → win-rate + CI (REQ-VEVAL-012).
6. **Formula-drift.** Within each arm, `arm_drift(passages, struct_of=…, analogy_of=…)`
   using `default_struct_tokens` for the POS skeletons (REQ-VEVAL-013).
7. **(Optional) detector** — advisory only, never gates (REQ-VEVAL-014).
8. **Report.** `evaluate_success(...)` then `render_report(...)`. v2 passes only when it
   is floor-clean, scores higher on the positive signals, wins >50% pairwise,
   trustworthiness is not worse, and drift is lower (REQ-VEVAL-015).

## Human study (later run)
`build_study(pairs, seed, rubric)` builds the ≥50–60-item blind A/B scaffold;
`fleiss_kappa(...)` measures inter-rater reliability; `graduate(...)` is the gate that
promotes a signal from advisory to gating only on a moderate positive Spearman
correlation whose CI excludes zero, never degrading trustworthiness (REQ-VEVAL-016/017).

## Helpers
`scripts/prompts.py`, `arms.py`, `floor_gate.py`, `signal_deltas.py`, `ballot.py`,
`winrate.py`, `drift.py`, `detector.py`, `report.py`, `human_study.py`,
`sibling_skills.py`. All deterministic and unit-tested; siblings loaded repo-first.
