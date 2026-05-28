# Preregistered falsification conditions

These conditions are preregistered BEFORE the v3.1 essay is written. Recorded
here so the eventual audit cannot be reverse-engineered to pass.

The design fails if **either** of these conditions holds in the v3.1 audit:

## Condition 1 — Monotone move-frequency

`chassis_judge.most_frequent_move_frequency` for v3.1 is ≥ 0.50. Half or more
of the paragraphs executing one move-shape is the chassis fault by the LLM-judge's
own taxonomy; if this holds, the design did not break the metronome.

## Condition 2 — Critique names the chassis

`chassis_judge.unsympathetic_critique` for v3.1 contains any of the substrings:
`"chassis"`, `"template"`, `"metronome"`, `"one move"`, `"same move"`,
`"every paragraph"`, OR matches the regex
`r"\b(perform|performing)\b.{0,20}\b(wisdom|insight|moral)\b"`. The LLM-judge
naming the fault in v3.1 is the design's failure regardless of the deterministic
linter numbers.

Either condition triggering means the design did not work. The audit must record
the outcome honestly, including in the failure case. There is no condition under
which "the linter numbers moved" is sufficient to declare success without the
chassis-judge also clearing.

## Honest caveats

- **Single-author non-blind rewrite.** I wrote v3, received the critique, designed
  the response, and am now writing v3.1 knowing the test. The Goodhart concern is
  real and the design admits it; preregistration is the only available
  pre-commitment that the audit can be checked against.
- **I am both writer and judge.** With no separate LLM available in this
  environment, the chassis_judge step is run by me (the orchestrator) acting as
  the LLM through the dispatcher interface. The dispatcher's response is recorded
  verbatim; the parser produces the result; the falsification check is mechanical
  on the parsed output. The judging is intended to be consistent across v3 and
  v3.1 (same prompt, same author, applied with the same care). The audit README
  discloses this constraint and proposes a future-iteration external-judge step
  as the cleaner protocol.
- **What the instruments do and do not measure.** The two deterministic linters
  catch surface monotony signatures (shape variance, closer density). The
  chassis_judge catches the move-level chassis. The reading council scores
  enjoyment/flow/style/quality. None of them is a substitute for a blind external
  reader; the audit is the suite scoring its own output.
