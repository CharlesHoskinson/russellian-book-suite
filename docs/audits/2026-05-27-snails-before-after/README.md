# Snails: before / after — a voice rewrite measured by the suite

Date: 2026-05-27

Two essays on the same subject (snails) in Bertrand Russell's voice. `v1` was written
first; an external reader judged it "more decorative than Russell" — strong in spirit
(8/10) but weaker in execution (6/10), because nearly every paragraph ran the same
circuit (fact → reversal → epigram) and lingered on natural-history detail rather than
moving to the argument. `v2` applies the correction: state the principle first and argue
it, vary the texture (let paragraphs rest plainly, reserve the turn), and treat the snail
as an instrument rather than an ornament.

Both essays were then scored by the suite's own instruments — the Russell-Delta scorer
(`russellian-style`) and the reading council (`review-conductor`).

## Result

| metric | v1 (decorative) | v2 (argument-forward) | reads as |
|---|---|---|---|
| Russell-Delta | 0.830 (edge) | 0.835 (edge) | unchanged |
| Enjoyment | 4.0 | 3.5 | down |
| Flow | 3.5 | 4.0 | up |
| Style | 4.0 | 4.0 | flat |
| Quality | 3.0 | 4.0 | up |
| Overall | 3.62 | 3.88 | up |
| Flesch | 67.6 | 67.4 | flat ("plain") |
| burstiness | 0.375 | 0.484 | up (more varied) |

## Reading

Each instrument shows its blind spot and its strength:

- The **Russell-Delta scorer is blind to the rewrite** (0.83 → 0.83): it measures the
  function-word fingerprint, which is identical across both essays, so it cannot
  distinguish relentless decoration from argued prose.
- The **reading council captured exactly what the human reader did.** It decomposed the
  trade: v1 scores highest on enjoyment (4.0) but lowest on quality (3.0) — the external
  "8/10 spirit, 6/10 prose" rendered as numbers. The correction traded a little surface
  dazzle (enjoyment 4.0 → 3.5) for real gains in flow (3.5 → 4.0) and quality (3.0 → 4.0),
  lifting overall 3.62 → 3.88.
- **Burstiness rose** (0.375 → 0.484): the rewrite's sentence lengths vary more, a small
  human-prose signal that corroborates the flow gain.

The rewrite is measurably more Russell-as-a-craftsman (substance, varied texture) at a
slight cost in Russell-as-a-showman (the jeweled line) — the right trade, since the
showman uniformity was the tell the reader flagged.

Essays: `snails-v1-decorative.md`, `snails-v2-argument-forward.md`.
