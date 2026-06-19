# Spec delta — russellian-voice

Capability: `VOICE` (russellian-voice)
Delta against `openspec/specs/russellian-voice/spec.md`. REQ-VOICE-001..007 exist;
this change ADDs REQ-VOICE-008..012 and MODIFYs the rhythm rule's behaviour via the
v2 ruleset. The v1 ruleset is unchanged.

## ADD REQ-VOICE-008 — Ubiquitous

The russellian-style linters shall accept a `--ruleset` selector and a `--register`
selector. The v1 ruleset (`assets/russellian-rules.json`) shall remain byte-frozen;
the v2 behaviour shall live in `assets/russellian-rules-v2.json`.

## ADD REQ-VOICE-009 — Event-driven (rhythm drumbeat exemption)

When the v2 ruleset is selected and a repeated-opening run is detected, the rhythm
linter shall exempt the run and record a `parallel-list` credit if all hold: the
repeated opener is syntactically shallow (a determiner, pronoun, or function word);
the following head nouns or predicates are semantically distinct and progressive;
the clause lengths are not mechanically identical (character-length variance above
~30 percent, or a monotonic climax gradient); and the run is capped by a synthesis or
turn sentence within one to two sentences. Otherwise the run shall remain a cadence
defect.

## MODIFY rhythm rule — v1 unchanged, v2 exempts drumbeats

Under the v1 ruleset the repeated-opening rule shall behave exactly as before (so the
20×20 control is reproducible). Under the v2 ruleset it shall apply REQ-VOICE-009.

## ADD REQ-VOICE-010 — State-driven (register-conditioned modifier corridor)

While the v2 ruleset is active, the signal-density linter shall enforce a
register-conditioned modifier corridor (tighter for technical-exposition, relaxed for
narrative-editorial, moderate for polemic) drawn from corpus percentiles, replacing
the global 0.25 budget.

## ADD REQ-VOICE-011 — Ubiquitous (accuracy floor invariant)

The accuracy floor — atomicity, no hedging, epistemic precision, and the
agentless/evasive passive constraint — shall be identical across all registers and
across v1 and v2 rulesets. Only texture dials (modifier budget, cadence corridor)
shall vary by register.

## ADD REQ-VOICE-012 — Optional feature (passive end-focus exemption)

Where a passive construction serves end-focus or topic continuity and names or
clearly implies its agent, the v2 ruleset may exempt it; the floor shall continue to
flag agentless or agent-suppressing passive constructions.
