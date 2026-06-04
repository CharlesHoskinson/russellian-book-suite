# Voice-eval demonstration bundle — 2026-05-27

**Topic:** the foundations of mathematical certainty
**Mode:** technical-exposition
**Paragraphs:** 30 original paragraphs in Russell's voice (`generated.md`)
**Baseline:** a genuine Russell excerpt — his essay *Mathematics and the Metaphysicians* (`C:\Users\charl\AppData\Local\Temp\compare\real-russell-math.md`)

This bundle exercises the new comparison stage (`scripts.voice_eval`): it scores the
generated prose against the Russell-Delta profile, scores a real Russell excerpt the
same way, and prints the two side by side together with the full linter battery. Full
output is in `report.md`; the script command is recorded below.

## Headline numbers (from `report.md`)

| | Russell-Delta | verdict |
|---|---:|---|
| generated (2,431 words) | **0.884234** | at the edge of Russell's range |
| Russell baseline (1,820 words) | **0.791921** | at the edge of Russell's range |

Band for reference: p50 = 0.684914, p90 = 0.786404. The "edge" verdict covers the
zone between p90 and the upper fence; both texts land there, which is itself a useful
calibration check — the genuine Russell excerpt is *also* at the edge of the profile's
centre, not snug inside p90.

## Honest read

The generated prose lands in the same verdict band as real Russell ("at the edge of
Russell's range"), but it does not get there cheaply, and on the headline metric it is
the weaker of the two: its Delta of 0.884 sits about 0.092 further from Russell's
centroid than the genuine excerpt's 0.792, and both already sit above p90. The closest
match is on hedging, where the densities are almost indistinguishable (11.52 vs 11.54
per 1,000 words) — the generated prose qualifies its claims at Russell's rate. Where it
diverges, it diverges in two opposite directions. It is markedly *more active and
plainer* than Russell on the surface: passive-voice density is half his (10.28 vs
20.88), signal density is well below his (6.58 vs 11.54), and sentence-rhythm flags are
a quarter of his (0.82 vs 3.85) — the contract's "atomic, active-voice" discipline pulls
the prose away from Russell's own fondness for the passive and the long suspended period.
In the other direction it over-qualifies: epistemic-precision density is more than double
Russell's (4.11 vs 1.65), so the generated text actually hedges its epistemics *harder*
than Russell did in this essay. The remaining linters are near-zero for both texts and
carry little signal at this length (parallel_structure, listicle_abstract, burstiness and
ai_vocabulary are 0.0 on both; concrete_instance_density, ai_staccato and paragraph_motion
fire once in the baseline and not at all in the generated text). The fair summary: the
imitation is recognisably Russellian in vocabulary-distribution and hedging, but it is
cleaner, more clipped and more cautious than the real article, and on the single
similarity number it scores worse than the man himself.

## Reproduce

```
cd /c/russellian-book-suite/skills/russellian-style
.venv/Scripts/python.exe -m scripts.voice_eval \
  ../../docs/audits/2026-05-27-voice-eval/generated.md \
  "C:\Users\charl\AppData\Local\Temp\compare\real-russell-math.md" \
  ../../docs/audits/2026-05-27-voice-eval/report.md
```

## Files

- `generated.md` — the 30 generated paragraphs (prose only)
- `report.md` — full voice-eval output (Deltas, verdicts, linter table, prose)
- `README.md` — this bundle summary
