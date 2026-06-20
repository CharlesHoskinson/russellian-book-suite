# Phase 6 review gate

Date: 2026-06-19

Scope: design-intelligence KG implementation for REQ-KG-047 through
REQ-KG-056.

## Spec-compliance review

| Requirement | Status | Evidence |
|---|---|---|
| REQ-KG-047 | Pass | `kg-schema.edn` declares `design-requirement`, `design-scenario`, `design-decision`, `test-case`, `ci-workflow`, `ci-job`, `operator-command`, and `traceability-link`; `test_kg_schema.py` validates source provenance. |
| REQ-KG-048 | Pass | `project_design_kg.py` extracts OpenSpec requirements and scenarios plus decisions, risks, non-goals, alternatives, and operator commands with source paths and lines. Fixture tests assert byte-identical inputs after projection. |
| REQ-KG-049 | Pass | Traceability rows carry kind, confidence, witness, provenance, and promoted status. Ambiguous and lexical links stay evidence-only. |
| REQ-KG-050 | Pass | Test and CI extraction covers pytest/Rust/cljs tests, workflows, jobs, required-gate inference, matrix selectors, and primary commands. |
| REQ-KG-051 | Pass | `design_kg_queries.py` exposes `impact`, `why`, `coverage-gaps`, `stale-docs`, `untested-god-nodes`, `claim-grounding`, and `ci-gates`. |
| REQ-KG-052 | Pass | Query tests require source path and line provenance for every returned row. `why` now includes OpenSpec scenario evidence. |
| REQ-KG-053 | Pass | Extractors are read-only and deterministic over sorted paths/rows; fixture tests assert repeated snapshots and unchanged inputs. |
| REQ-KG-054 | Partial/advisory | `coverage-map.md` maps graphify community samples to promoted/evidence traceability and flags large uncovered samples. Full community membership and claim mapping remain limited by graphify report data and are advisory, not merge-gating. |
| REQ-KG-055 | Pass | Tests prove ambiguous exact-symbol and weak lexical candidates are not promoted. Canonical queries use promoted links only. |
| REQ-KG-056 | Pass | `snapshot-summary.json` records commit, graphify version, projection commands, report paths, graph counts, and projection counts. |

## Code-quality review

- Backend isolation: passed. `test_no_module_bypasses_seam` confirms only
  `scripts/cozo_store.py` imports `pycozo`.
- Determinism: passed for the fixture. Extractors sort paths and output rows,
  use stable ids, and leave inputs unchanged.
- Source provenance: passed for schema, projectors, and query rows. Every
  design/test/CI/query row has a source path and line, or a synthetic source for
  audit-builder query errors.
- Promotion discipline: passed. Evidence-only rows are visible through
  `stale-docs`, but excluded from `impact`, `why`, `coverage-gaps`, and
  `ci-gates` canonical traversals.

## Gate decision

Merge-gating:

- Fixture-level schema, extractor, traceability, query, audit-builder, and
  backend-seam tests now run in the always-run `tools + design KG` CI job.

Advisory:

- Full graphify generation and `docs/audits/<date>-design-intelligence-kg/`
  snapshots remain advisory. They require a local graphify install and ignored
  `graphify-out/` inputs, so they should not block merges until graphify runtime
  pinning and cache policy are added.

## Local validation

Passed:

- `python -m pytest skills/book-knowledge/tests/test_design_kg_audit.py skills/book-knowledge/tests/test_design_kg_queries.py skills/book-knowledge/tests/test_project_design_kg.py skills/book-knowledge/tests/test_design_kg_fixture.py skills/book-knowledge/tests/test_kg_schema.py skills/book-knowledge/tests/test_cozo_store_contract.py -q`
- `python -m pytest ci/test_compute_matrix.py ci/test_lint_no_direct_http.py ci/test_no_shadow_writes.py -q`
- Workflow YAML parse over `.github/workflows/*.yml`
- `git diff --check`
- ASCII scan over new design-KG scripts/tests/docs/audit artifacts

Not run locally:

- `nix flake check -L`: `nix` is not installed in this Windows shell.
- `actionlint`: `actionlint` is not installed in this Windows shell.

## Residual risks

- Graphify community coverage is conservative because `GRAPH_REPORT.md` exposes
  samples, not complete per-community membership. Fix path: project graphify
  community ids/ranks into `code-node` or consume a graphify export that carries
  full membership.
- `claim-grounding` returns no rows in the current audit because the audit
  builder projects code/design/test/CI data, not the full claim ledger. Fix path:
  add a ledger projection stage to the audit builder when claim-backed design
  review becomes a gate.
- Archived OpenSpec requirements dominate `coverage-gaps`. Fix path: either
  exclude archived changes from active coverage queries or move old archive
  specs outside the active design-audit input set.
