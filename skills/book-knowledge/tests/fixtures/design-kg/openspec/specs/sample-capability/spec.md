# Capability: sample-capability

## Requirements

### Requirement: REQ-KG-901 - Fixture requirement (Ubiquitous)

The fixture SHALL expose a deterministic design graph input that links a
requirement, design decision, test case, CI job, and graphify code node.
The fixture implementation source is `src/fixture.py`.

Rationale: the design-intelligence KG extractors need a compact fixture with all
first-pass entity families present.

#### Scenario: fixture requirement is covered by a test

- **WHEN** the design-KG extractor reads this fixture
- **THEN** it emits a `design-requirement` row for `REQ-KG-901`
- **AND** `tests/test_fixture_pipeline.py::test_REQ_KG_901_fixture_requirement` covers it
