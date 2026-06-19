# Design — HFR v2

The full technical design is `docs/specs/2026-06-19-hfr-v2-liveliness-design.md`.
This file records only the change-local technical approach and the decisions that
shape the spec deltas.

## Approach: separated v2 skills, v1 frozen

Five units plus one shared artifact. The negative floor stays hard and separate
from the advisory positive signals; the floor never imports the signals; the
generator consults both. v1 is frozen two ways: the v1 `russellian-rules.json`
ruleset is untouched (the floor is versioned by ruleset, not by forking the skill),
and the v1 `triadic-voice` skill is left as-is to serve as the 20×20 control.

## Capabilities touched

| Capability (slug) | Delta |
|---|---|
| `liveliness-signals` (LIVE) | new — corpus profiler + 8 advisory scorers + regression set |
| `russellian-voice` (VOICE) | v2 ruleset: drumbeat exemption + register corridor |
| `triadic-voice` (TRIAD) | new — register router, chassis library, plan-then-adapt, anti-copy |
| `voice-eval` (VOICE-EVAL) | new — 20×20 harness, formula-drift monitor, human-study scaffold |

## Key engineering decisions

- **Corpus profile is statistics-only**, per register, deterministic for fixed
  input — copyright-safe and consumed by both linters (thresholds) and the
  generator (targets).
- **Verb-energy detects light-verb + event-noun constructions** with a profile
  allow-list, not suffix counts (cmp-lg/9503010).
- **Cadence is a two-sided percentile corridor** flagging both metronomic and
  erratic prose; coupled with novelty-continuity coherence so short-punchline
  padding cannot game it (1805.01460).
- **All positive signals advisory in phase 1.** Graduation to a gate requires the
  human-correlation study. AI detectors never gate (2412.05139).
- **The judge runs in-session** (no API): the self-preference bias cancels because
  both 20×20 arms are LLM-generated (2303.16634); order-swap + length-match handle
  position/verbosity bias.
- **Graceful degradation**: a missing lexicon or spaCy model emits an explicit WARN
  row, never a silent skip.

## Sequencing

Profile → floor ruleset → signals → generation v2 → eval harness. The exhaustive
TDD plan is produced via the writing-plans skill; `tasks.md` is the lightweight
checklist citing REQ IDs.
