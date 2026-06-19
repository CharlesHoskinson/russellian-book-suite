# Graphify code map

This repo keeps `graphify-out/` ignored. The graph is an operator artifact:
regenerate it locally when doing architecture, CI, or dependency analysis.

## Current local run

Generated on 2026-06-19 from commit `52632ecc` with graphify `0.8.35`.

- Raw code graph: 15,252 nodes, 51,848 edges.
- Cluster report: 15,206 nodes, 23,087 edges, 1,306 communities.
- Benchmark: about 69x fewer tokens per architecture query than reading the
  corpus naively.

The 46-node difference between raw graph and cluster report is graphify's
post-cluster fuzzy deduplication. Treat `graphify-out/graph.json` as the raw
source graph and `graphify-out/GRAPH_REPORT.md` as the navigation report.

## Regenerate

The console script may not be on `PATH` in fresh Windows shells, so use the
module form:

```powershell
python -m pip install --user graphifyy
python -m graphify update . --no-cluster --force
python -m graphify cluster-only . --no-viz --no-label
python -m graphify benchmark graphify-out\graph.json
```

`update` is the no-LLM path for code extraction. Full semantic extraction is
slower and will use the configured model backend if one is available.

## Query

Use graphify before broad source sweeps:

```powershell
python -m graphify query "project_graphify code claim link cozo store" --budget 2500
python -m graphify explain "CozoStore"
python -m graphify path "project_graphify()" "code_claim_autolink.py"
python -m graphify diagnose multigraph --json
```

Useful local findings from the current graph:

- `project_graphify()` is the entry point that loads graphify `graph.json` into
  `code-node` and `code-edge`.
- `code_claim_autolink.py` materializes deterministic links between code nodes
  and claims.
- `test_kg_capability.py` exercises the cross-graph query path that joins
  graphify code nodes, code edges, code-claim links, and verified claims in one
  `CozoStore`.
- CI behavior is centralized in `.github/workflows/ci.yml`,
  `.github/ci/skills-matrix.json`, `ci/compute_matrix.py`, and the
  `ci-required` aggregator.

## Scope

`.graphifyignore` intentionally excludes historical audits, eval outputs,
generated QA JSON, release artifacts, local venvs, and large style corpora.
Those files are useful records, but they distort the live architecture map.
