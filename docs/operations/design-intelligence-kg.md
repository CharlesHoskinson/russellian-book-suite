# Design-intelligence KG runbook

The design-intelligence KG projects OpenSpec requirements, design docs, tests,
CI jobs, graphify code nodes, and deterministic traceability into one local
Cozo store. Use it when an agent needs evidence-backed answers about design
impact, coverage gaps, stale docs, or CI gates.

## Inputs and outputs

- `graphify-out/graph.json`: local code graph input. This stays ignored.
- `graphify-out/GRAPH_REPORT.md`: local graphify community report. This stays
  ignored.
- `skills/book-knowledge/assets/kg-schema.edn`: canonical KG schema.
- `docs/audits/<date>-design-intelligence-kg/`: committed audit artifact.

Promoted traceability links are exact deterministic links. Evidence-only links
are review candidates and must not be treated as canonical design truth until a
human or later rule promotes them.

## Regenerate graphify

Run from the repo root. The console script is not always on `PATH` in Windows
shells, so prefer module form:

```powershell
python -m pip install --user graphifyy
python -m graphify update . --no-cluster --force
python -m graphify cluster-only . --no-viz --no-label
python -m graphify benchmark graphify-out\graph.json
```

`update` is the no-LLM extraction path. `cluster-only` refreshes
`GRAPH_REPORT.md`, which the audit uses for community coverage.

## Build the audit

```powershell
python skills/book-knowledge/scripts/build_design_kg_audit.py --root . --out docs/audits/2026-06-19-design-intelligence-kg --date 2026-06-19
```

Use a new dated output directory for a new snapshot. Commit the audit directory,
not `graphify-out/`.

The builder writes:

- `snapshot-summary.json`: metadata, row counts, and query result counts.
- `README.md`: human index for the snapshot.
- `coverage-map.md`: graphify community samples with traceability hit counts.
- `findings.md`: coverage gaps, stale-doc evidence, and untested high-rank
  node summaries.
- `queries.md`: sample rows for `impact`, `why`, `coverage-gaps`,
  `stale-docs`, `untested-god-nodes`, `claim-grounding`, and `ci-gates`.

## Read the results

Start with `snapshot-summary.json` to check whether the graph is complete. Then
read `findings.md`:

- `coverage-gaps` means a requirement is missing at least one promoted
  implementation, test, or CI link.
- `stale-docs` means text matched code weakly or ambiguously. Inspect the
  witness before changing code or promoting the link.
- `untested-god-nodes` means a high-rank code node has no promoted
  `test-exercises-code` link.

Archived OpenSpec requirements may appear in `coverage-gaps`. Treat those as
taxonomy cleanup unless the `status` should be restored to active work.

## Validate changes

```powershell
python -m pytest skills/book-knowledge/tests/test_design_kg_audit.py skills/book-knowledge/tests/test_design_kg_queries.py skills/book-knowledge/tests/test_project_design_kg.py skills/book-knowledge/tests/test_design_kg_fixture.py skills/book-knowledge/tests/test_kg_schema.py skills/book-knowledge/tests/test_cozo_store_contract.py -q
git diff --check
```

## Gate policy

The fixture-level schema, extractor, query, audit-builder, and backend-seam
tests are merge-gating through the always-run `tools + design KG` CI job. These
checks do not require graphify, network access, or committed generated graph
files.

The whole-repo graphify audit is advisory. Keep it committed when producing a
design snapshot, but do not make `graphify-out/` or full graph generation a
merge gate unless the project first adds a pinned graphify runtime and cache
strategy. The advisory audit is still source-backed: every query sample carries
`source_path` and `source_line`, and evidence-only links remain non-canonical.

If a promoted link looks wrong, add or adjust fixture coverage before changing
the projector. If an evidence-only link is useful, prefer adding exact path,
symbol, requirement ID, or CI command evidence over broadening lexical matching.
