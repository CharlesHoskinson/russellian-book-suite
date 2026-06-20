# Design-intelligence KG audit

- date: 2026-06-19
- commit: 7e6283b
- graphify version: graphify 0.8.35
- graphify graph: graphify-out/graph.json

## Counts

- requirements: 131
- design scenarios: 205
- design decisions: 116
- operator commands: 4170
- tests: 2292
- ci workflows: 5
- ci jobs: 24
- traceability links: 233
- promoted links: 191
- evidence only links: 42
- graph nodes: 15206
- graph edges: 27011

## Reproduce

- `python -m graphify update . --no-cluster --force`
- `python -m graphify cluster-only . --no-viz --no-label`
- `python skills/book-knowledge/scripts/build_design_kg_audit.py --root . --out docs/audits/<date>-design-intelligence-kg --date <date>`

## Files

- `snapshot-summary.json`: machine-readable counts and query sizes.
- `coverage-map.md`: graphify community samples and trace hits.
- `findings.md`: coverage gaps, stale evidence, and test gaps.
- `queries.md`: reproducible named query samples with provenance.
- `study-map.json` / `study-map.md`: AI-facing priority map.
- `review-gate.md`: Phase 6 compliance and code-quality review.
