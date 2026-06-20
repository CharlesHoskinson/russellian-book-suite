# Design KG fixture

Small deterministic input tree for the design-intelligence KG extractors.

The fixture has one of each first-pass input:

- OpenSpec requirement: `openspec/specs/sample-capability/spec.md`
- Design decision: `docs/design.md`
- Test case: `tests/test_fixture_pipeline.py`
- CI workflow/job: `.github/workflows/ci.yml`
- Graphify-shaped code graph: `graphify/graph.json`

Extractor tests should read this tree only and must not mutate it.
