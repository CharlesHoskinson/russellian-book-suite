# AI study map

This file turns raw design-KG query results into a prioritized map for
agents that need to improve design, utility, or traceability.

## Summary

- capabilities with work: 9
- active coverage gaps: 0
- archived coverage gaps: 92
- stale evidence links: 38
- reviewable evidence links: 2
- ambiguous evidence links: 36
- top priority: 2026-05-11-bundle-c-closed-loop-ledger-design.md

## Agent Workflow

- Start with active_coverage_gaps before archived_coverage_gaps.
- Inspect each example source_path/source_line before changing code.
- Promote evidence-only links only when exact identifiers, paths, or reviewed design evidence support them.
- For archived-only gaps, prefer documenting historical status over implementing stale requirements.

## Priorities

### 2026-05-11-bundle-c-closed-loop-ledger-design.md

- priority score: 100
- active coverage gaps: 0
- archived coverage gaps: 0
- stale evidence links: 1
- reviewable evidence links: 1
- ambiguous evidence links: 0
- missing implementation/test/ci: 0/0/0
- recommended action: review evidence-only links and promote only exact, source-backed matches

- example: stale-evidence docs/specs/2026-05-11-bundle-c-closed-loop-ledger-design.md:229

### 2026-06-03-carve-completion-design.md

- priority score: 100
- active coverage gaps: 0
- archived coverage gaps: 0
- stale evidence links: 1
- reviewable evidence links: 1
- ambiguous evidence links: 0
- missing implementation/test/ci: 0/0/0
- recommended action: review evidence-only links and promote only exact, source-backed matches

- example: stale-evidence docs/superpowers/specs/2026-06-03-carve-completion-design.md:16

### homoiconic-kg

- priority score: 53
- active coverage gaps: 0
- archived coverage gaps: 41
- stale evidence links: 12
- reviewable evidence links: 0
- ambiguous evidence links: 12
- missing implementation/test/ci: 35/41/41
- recommended action: confirm archived requirements are historical, then keep them out of active design gates

- example: ambiguous-evidence openspec/specs/homoiconic-kg/spec.md:65
- example: ambiguous-evidence openspec/specs/homoiconic-kg/spec.md:65
- example: ambiguous-evidence openspec/specs/homoiconic-kg/spec.md:145
- example: ambiguous-evidence openspec/specs/homoiconic-kg/spec.md:145
- example: ambiguous-evidence openspec/specs/homoiconic-kg/spec.md:145

### proof-obligations

- priority score: 33
- active coverage gaps: 0
- archived coverage gaps: 9
- stale evidence links: 24
- reviewable evidence links: 0
- ambiguous evidence links: 24
- missing implementation/test/ci: 7/9/9
- recommended action: confirm archived requirements are historical, then keep them out of active design gates

- example: ambiguous-evidence openspec/specs/proof-obligations/spec.md:34
- example: ambiguous-evidence openspec/specs/proof-obligations/spec.md:34
- example: ambiguous-evidence openspec/specs/proof-obligations/spec.md:34
- example: ambiguous-evidence openspec/specs/proof-obligations/spec.md:34
- example: ambiguous-evidence openspec/specs/proof-obligations/spec.md:34

### attributed-generation

- priority score: 14
- active coverage gaps: 0
- archived coverage gaps: 14
- stale evidence links: 0
- reviewable evidence links: 0
- ambiguous evidence links: 0
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
- reviewable evidence links: 0
- ambiguous evidence links: 0
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
- reviewable evidence links: 0
- ambiguous evidence links: 0
- missing implementation/test/ci: 7/7/7
- recommended action: confirm archived requirements are historical, then keep them out of active design gates

- example: coverage-gap openspec/changes/archive/2026-06-18-kg-argumentation-layer/specs/argumentation/spec.md:27
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-argumentation-layer/specs/argumentation/spec.md:44
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-argumentation-layer/specs/argumentation/spec.md:59
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-argumentation-layer/specs/argumentation/spec.md:73
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-argumentation-layer/specs/argumentation/spec.md:88

### kg-prose-eval

- priority score: 7
- active coverage gaps: 0
- archived coverage gaps: 7
- stale evidence links: 0
- reviewable evidence links: 0
- ambiguous evidence links: 0
- missing implementation/test/ci: 7/7/7
- recommended action: confirm archived requirements are historical, then keep them out of active design gates

- example: coverage-gap openspec/changes/archive/2026-06-18-kg-prose-eval-harness/specs/kg-prose-eval/spec.md:24
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-prose-eval-harness/specs/kg-prose-eval/spec.md:46
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-prose-eval-harness/specs/kg-prose-eval/spec.md:69
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-prose-eval-harness/specs/kg-prose-eval/spec.md:84
- example: coverage-gap openspec/changes/archive/2026-06-18-kg-prose-eval-harness/specs/kg-prose-eval/spec.md:95

### claim-first-drafting

- priority score: 6
- active coverage gaps: 0
- archived coverage gaps: 6
- stale evidence links: 0
- reviewable evidence links: 0
- ambiguous evidence links: 0
- missing implementation/test/ci: 6/6/6
- recommended action: confirm archived requirements are historical, then keep them out of active design gates

- example: coverage-gap openspec/changes/archive/2026-06-18-live-chapter-bundle-input/specs/claim-first-drafting/spec.md:23
- example: coverage-gap openspec/changes/archive/2026-06-18-live-chapter-bundle-input/specs/claim-first-drafting/spec.md:38
- example: coverage-gap openspec/changes/archive/2026-06-18-live-chapter-bundle-input/specs/claim-first-drafting/spec.md:53
- example: coverage-gap openspec/changes/archive/2026-06-18-live-chapter-bundle-input/specs/claim-first-drafting/spec.md:68
- example: coverage-gap openspec/changes/archive/2026-06-18-live-chapter-bundle-input/specs/claim-first-drafting/spec.md:84
