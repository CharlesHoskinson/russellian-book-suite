# Reading-council demo — scoring the repo README

Date: 2026-05-27

The four-persona reading council (enjoyment-reader, gottlieb, lay-reader,
first-time-visitor) scored the repository `README.md` against
`review-conductor/assets/reading-rubric.md`. Per-persona 1-5 scores were aggregated by
median into a single synthesized `reading-score.json` (see this directory). No
per-persona transcript is surfaced — the council is internal.

## Result

| dimension | score |
|---|---|
| enjoyment | 3.0 |
| flow | 3.5 |
| style | 4.0 |
| quality | 4.0 |
| **overall** | **3.62 / 5** |

Deterministic anchors (reported alongside, not blended): **Flesch Reading Ease 52.53**
("plain" register), **burstiness 1.031** (standard deviation of sentence length over its
mean).

## Honest read

The README is strongest on **style** (4.0) and **quality** (4.0): a present, consistent
voice and a sound structure. **Enjoyment is the weakest dimension (3.0)** — the opening
"Tuesday-morning editor" scene hooks, but the middle (the skill tables and the QA
grammar) is reference-dense and reads slower, which is precisely the staleness this
metric is meant to surface. The burstiness of 1.03 is a healthy human signal — far above
the 0.2-0.4 band typical of flat machine prose — and the "plain" Flesch is appropriate
for a technical audience. The number to watch over time is enjoyment: if it drifts down
as sections are added, the prose is going stale.

## What this exercises

`run_reading_council` / `aggregate_reading_scores` (median, synthesized verdict),
`flesch_reading_ease`, `burstiness`, the `documentation` panel, and the reading rubric —
the advisory enjoyment metric grounded in Strunk-White, Sol Stein, and the Narrative
Transportation Scale.
