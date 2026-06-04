# Spec delta — reading-council

Capability: `READING` (reading-council)
Delta against `openspec/specs/reading-council/spec.md` (new capability; all ADD).

## ADD REQ-READING-001 — Ubiquitous

`review-conductor` shall provide a reading rubric asset defining four dimensions —
enjoyment, flow, style, quality — each with anchored 1-5 descriptors grounded in the
named craft references (Strunk-White, Sol Stein, the Narrative Transportation Scale).

## ADD REQ-READING-002 — Ubiquitous

A documentation-scope scoring panel shall exist (`panels/documentation.yaml`,
`artifact_scope: documentation`) naming the council personas used for scoring.

## ADD REQ-READING-003 — Event-driven

When the scoring dispatch runs, each persona packet shall request the four dimension
scores (1-5) plus a one-line justification, evaluated against the shared rubric.

## ADD REQ-READING-004 — Event-driven

When reading scores are aggregated, the aggregator shall compute the median per dimension
across personas and an overall score, and shall emit a single `reading-score.json`
carrying the four dimension scores, the overall, the deterministic anchors, and a verdict.

## ADD REQ-READING-005 — Ubiquitous

The reading-score output shall contain one synthesized verdict in a single voice and
shall not include any per-persona transcript or quotation.

## ADD REQ-READING-006 — Ubiquitous

The output shall include deterministic anchors — Flesch Reading Ease and a burstiness
measure — reported alongside, not blended into, the rubric scores.

## ADD REQ-READING-007 — Ubiquitous

Reading-council scoring shall be advisory: it shall not gate, fail, or block any pipeline.

## ADD REQ-READING-008 — Ubiquitous

The scoring shall make no live LLM calls of its own (the dispatcher is caller-provided),
and the aggregation and deterministic anchors shall be deterministic and require no
network.
