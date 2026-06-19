# AI study map

This file turns raw design-KG query results into a prioritized map for
agents that need to improve design, utility, or traceability.

## Summary

- capabilities with work: 9
- active coverage gaps: 24
- archived coverage gaps: 97
- stale evidence links: 42
- top priority: proof-obligations

## Agent Workflow

- Start with active_coverage_gaps before archived_coverage_gaps.
- Inspect each example source_path/source_line before changing code.
- Promote evidence-only links only when exact identifiers, paths, or reviewed design evidence support them.
- For archived-only gaps, prefer documenting historical status over implementing stale requirements.

## Priorities

### proof-obligations

- priority score: 141
- active coverage gaps: 6
- archived coverage gaps: 9
- stale evidence links: 24
- missing implementation/test/ci: 13/15/15
- recommended action: add or promote traceability for active requirements covering ci, implementation, test

- example: coverage-gap openspec/changes/live-proof-gate/specs/proof-obligations/spec.md:29
- example: coverage-gap openspec/changes/live-proof-gate/specs/proof-obligations/spec.md:44
- example: coverage-gap openspec/changes/live-proof-gate/specs/proof-obligations/spec.md:58
- example: coverage-gap openspec/changes/live-proof-gate/specs/proof-obligations/spec.md:72
- example: coverage-gap openspec/changes/live-proof-gate/specs/proof-obligations/spec.md:86

### claim-first-drafting

- priority score: 126
- active coverage gaps: 12
- archived coverage gaps: 6
- stale evidence links: 0
- missing implementation/test/ci: 18/18/18
- recommended action: add or promote traceability for active requirements covering ci, implementation, test

- example: coverage-gap openspec/changes/live-code-grounding/specs/claim-first-drafting/spec.md:26
- example: coverage-gap openspec/changes/live-code-grounding/specs/claim-first-drafting/spec.md:41
- example: coverage-gap openspec/changes/live-code-grounding/specs/claim-first-drafting/spec.md:56
- example: coverage-gap openspec/changes/live-code-grounding/specs/claim-first-drafting/spec.md:70
- example: coverage-gap openspec/changes/live-code-grounding/specs/claim-first-drafting/spec.md:85

### homoiconic-kg

- priority score: 94
- active coverage gaps: 0
- archived coverage gaps: 46
- stale evidence links: 16
- missing implementation/test/ci: 38/46/46
- recommended action: review evidence-only links and promote only exact, source-backed matches

- example: stale-evidence openspec/specs/homoiconic-kg/spec.md:65
- example: stale-evidence openspec/specs/homoiconic-kg/spec.md:65
- example: stale-evidence openspec/specs/homoiconic-kg/spec.md:145
- example: stale-evidence openspec/specs/homoiconic-kg/spec.md:145
- example: stale-evidence openspec/specs/homoiconic-kg/spec.md:145

### kg-prose-eval

- priority score: 67
- active coverage gaps: 6
- archived coverage gaps: 7
- stale evidence links: 0
- missing implementation/test/ci: 13/13/13
- recommended action: add or promote traceability for active requirements covering ci, implementation, test

- example: coverage-gap openspec/changes/live-eval-gate/specs/kg-prose-eval/spec.md:27
- example: coverage-gap openspec/changes/live-eval-gate/specs/kg-prose-eval/spec.md:42
- example: coverage-gap openspec/changes/live-eval-gate/specs/kg-prose-eval/spec.md:56
- example: coverage-gap openspec/changes/live-eval-gate/specs/kg-prose-eval/spec.md:72
- example: coverage-gap openspec/changes/live-eval-gate/specs/kg-prose-eval/spec.md:88

### attributed-generation

- priority score: 14
- active coverage gaps: 0
- archived coverage gaps: 14
- stale evidence links: 0
- missing implementation/test/ci: 14/14/14
- recommended action: confirm archived requirements are historical, then keep them out of active design gates

- example: coverage-gap openspec/changes/archive/2026-06-17-kg-writer-assertion-contract/specs/attributed-generation/spec.md:27
- example: coverage-gap openspec/changes/archive/2026-06-17-kg-writer-assertion-contract/specs/attributed-generation/spec.md:42
- example: coverage-gap openspec/changes/archive/2026-06-17-kg-writer-assertion-contract/specs/attributed-generation/spec.md:56
- example: coverage-gap openspec/changes/archive/2026-06-17-kg-writer-assertion-contract/specs/attributed-generation/spec.md:71
- example: coverage-gap openspec/changes/archive/2026-06-17-kg-writer-assertion-contract/specs/attributed-generation/spec.md:87

### chapter-retrieval

- priority score: 8
- active coverage gaps: 0
- archived coverage gaps: 8
- stale evidence links: 0
- missing implementation/test/ci: 8/8/8
- recommended action: confirm archived requirements are historical, then keep them out of active design gates

- example: coverage-gap openspec/changes/archive/2026-06-17-kg-chapter-retrieval-bundles/specs/chapter-retrieval/spec.md:23
- example: coverage-gap openspec/changes/archive/2026-06-17-kg-chapter-retrieval-bundles/specs/chapter-retrieval/spec.md:39
- example: coverage-gap openspec/changes/archive/2026-06-17-kg-chapter-retrieval-bundles/specs/chapter-retrieval/spec.md:54
- example: coverage-gap openspec/changes/archive/2026-06-17-kg-chapter-retrieval-bundles/specs/chapter-retrieval/spec.md:65
- example: coverage-gap openspec/changes/archive/2026-06-17-kg-chapter-retrieval-bundles/specs/chapter-retrieval/spec.md:81

### argumentation

- priority score: 7
- active coverage gaps: 0
- archived coverage gaps: 7
- stale evidence links: 0
- missing implementation/test/ci: 7/7/7
- recommended action: confirm archived requirements are historical, then keep them out of active design gates

- example: coverage-gap openspec/changes/archive/2026-06-18-kg-argumentation-layer/specs/argumentation/spec.md:27
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-argumentation-layer/specs/argumentation/spec.md:44
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-argumentation-layer/specs/argumentation/spec.md:59
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-argumentation-layer/specs/argumentation/spec.md:73
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-argumentation-layer/specs/argumentation/spec.md:88

### 2026-05-11-bundle-c-closed-loop-ledger-design.md

- priority score: 3
- active coverage gaps: 0
- archived coverage gaps: 0
- stale evidence links: 1
- missing implementation/test/ci: 0/0/0
- recommended action: review evidence-only links and promote only exact, source-backed matches

- example: stale-evidence docs/specs/2026-05-11-bundle-c-closed-loop-ledger-design.md:229

### 2026-06-03-carve-completion-design.md

- priority score: 3
- active coverage gaps: 0
- archived coverage gaps: 0
- stale evidence links: 1
- missing implementation/test/ci: 0/0/0
- recommended action: review evidence-only links and promote only exact, source-backed matches

- example: stale-evidence docs/superpowers/specs/2026-06-03-carve-completion-design.md:16
