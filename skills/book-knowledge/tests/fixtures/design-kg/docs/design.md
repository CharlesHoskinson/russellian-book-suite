# Fixture design

## Decision: keep design extraction deterministic

Status: accepted

The design-intelligence KG extracts authored requirements, decisions, tests, CI
jobs, and graphify code nodes from a fixed tree without mutating any input file.
The implementation source is `src/fixture.py`.

Rationale: deterministic extraction lets the graph participate in golden tests
and makes agent answers reviewable.

## Non-goal: infer canonical links from weak text similarity

Weak lexical or semantic matches may be stored as evidence, but this fixture
expects canonical links only from exact identifiers, paths, or reviewed evidence.

## Risk: stale design docs drift from tests

Mitigation: fixture tests compare canonical rows from the extractor.

## Alternative: infer decisions from commit history

Rejected: authored docs carry better review provenance than commit messages.

## Operator command: regenerate fixture graph

```powershell
python -m graphify skills/book-knowledge/tests/fixtures/design-kg/src --output graphify-out
```
