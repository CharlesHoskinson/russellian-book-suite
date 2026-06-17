# P4 graphify-fusion audit — 2026-06-17

GPT external audit of branch `feat/homoiconic-kg-p4` at `91dd4ed`. Verdict: READY-WITH-FIXES.

> **Resolution (2026-06-17).** All three findings fixed, TDD, on `feat/homoiconic-kg-p4`.
> **F1 (loader validation)** — added `_validate` to `project_graphify.py`: fail-fast
> `ValueError` on a structurally malformed graphify doc (missing/non-list `nodes`/`links`,
> node missing non-empty `id`, link missing `source`/`target`/`relation`, non-numeric
> `weight`). Crucially, the auditor's proposed fix (reject duplicate node ids and dangling
> edges) was REFUTED against the **real** `graph.json` (39,172 nodes / 818,069 links),
> which legitimately carries duplicate ids and ~7,575 dangling `ref_*` edges — hard-failing
> on those would have broken ingestion of actual graphify output. Validation therefore
> tolerates both (test `test_tolerates_real_graphify_quirks`), and a calibration check
> confirms the real file passes `_validate`. **F2 (capability not edge-sensitive)** — added
> `test_code_edge_traversal_to_claims` and `test_capability_query_is_edge_sensitive`, which
> join *through* a `code-edge` (module `contains` function → function backs verified claim),
> so dropping every code edge now fails the gate. **F3 (plan self-review overclaim)** —
> rewrote the plan self-review to state P4.1+P4.3 landed and P4.2 recompute/P4.4 CLI are
> deferred (not implemented). Suite **258 passed** (was 247; +8 validation, +1 tolerance,
> +2 edge-traversal). The 7 claims-to-verify the audit CONFIRMED remain confirmed.

## Verdict

READY-WITH-FIXES. The P4 branch passes the full book-knowledge suite and the cross-graph query is real: one CozoStore holds projected ledger claims, projected graphify code nodes/edges, and explicit code-claim links; the verified filter changes the result set. The main merge blocker I found is loader validation: malformed graphify documents are silently accepted, including missing top-level keys, dangling edges, missing `relation`, and duplicate node ids collapsing under Cozo upsert. There is also a test-rigor gap: the headline capability test passes even if graphify loads zero code edges, so it proves code-node-to-claim fusion, not full code-edge graph fusion.

## Test reproduction

Repository: fresh clone at `C:\Users\charl\AppData\Local\Temp\rbs-p4-audit`.

Branch/commits:

- P4: `feat/homoiconic-kg-p4` at `91dd4ed9e9fe3531a86f33c099fc7a4812f65dff`.
- Base: `origin/feat/homoiconic-kg-p0p1` at `310df68a35885ee473f8e33bc1fd543ea9c0d02a`.

Runner: Windows 11 (`Windows-11-10.0.26200-SP0`), Python `3.14.5`, pytest `9.1.0`.

Setup notes: `git clone` succeeded. A follow-up `git fetch origin feat/homoiconic-kg-p4 feat/homoiconic-kg-p0p1` failed once with `Could not connect to server`, but both remote refs were already present from clone. `python -m venv .venv` succeeded. Initial `.venv\Scripts\python.exe -m pip install -e .[dev]` failed under sandbox networking (`WinError 10013` to PyPI); rerunning with network approval succeeded and installed `pycozo[embedded]` / `cozo-embedded==0.7.6`.

Observed test results:

- `.venv\Scripts\python.exe -m pytest tests/ -q` -> `247 passed in 4.56s`.
- `.venv\Scripts\python.exe -m pytest tests/test_project_graphify.py tests/test_kg_capability.py -v` -> `4 passed in 0.15s`.

## Findings

1. [IMPORTANT] `project_graphify` accepts malformed graphify documents and persists bad graph state.

   - Location: `skills/book-knowledge/scripts/project_graphify.py:69`, `skills/book-knowledge/scripts/project_graphify.py:76`, `skills/book-knowledge/scripts/project_graphify.py:79`, `skills/book-knowledge/scripts/project_graphify.py:90`, `skills/book-knowledge/scripts/project_graphify.py:91`.
   - Problem: the loader uses `doc.get("nodes", [])` and `doc.get("links", [])`, defaults missing `relation` to `""`, never checks duplicate node ids, and never checks that link endpoints exist in `nodes`.
   - Evidence from live store probe:

     ```text
     missing_nodes OK nodes= [] edges= [['edge-653201935f667cb3', 'n1', 'n2', 'calls', 1.0]]
     missing_links OK nodes= [['n1', 'Node 1']] edges= []
     dangling_edge OK nodes= [['n1', 'one']] edges= [['edge-653201935f667cb3', 'n1', 'n2', 'calls', 1.0]]
     missing_relation OK ... edges= [['edge-79c76a15c5811faf', 'n1', 'n2', '', 1.0]]
     duplicate_node_ids OK nodes= [['n1', 'second']] edges= []
     missing_node_id ERR KeyError 'id'
     missing_link_source ERR KeyError 'source'
     missing_link_target ERR KeyError 'target'
     ```

   - Why it matters: a missing or malformed graph file can produce a green, empty or partial projection instead of a hard failure. Duplicate node ids silently overwrite earlier nodes through Cozo `:put`; dangling edges will disappear from endpoint-joined queries/algorithms; blank relationships create synthetic ids for invalid edges and can collapse multiple malformed links.
   - Proposed fix: add validation before `store.load`: require top-level `nodes` and `links` lists; require each node `id` to be a non-empty string and unique; allow `label: null` only if intentional; require each link `source`, `target`, and `relation` to be non-empty strings; require endpoints to be in the node id set; require `weight` to be numeric if present. Raise `ValueError` naming the bad index/key. Add tests for missing top-level keys, dangling edge, missing relation, duplicate node id, and missing required fields.
   - Must fix before merge: Yes.

2. [MINOR] The capability/acceptance test is not sensitive to code edges.

   - Location: `skills/book-knowledge/tests/test_kg_capability.py:61`, `skills/book-knowledge/tests/test_kg_capability.py:91`, `skills/book-knowledge/tests/test_kg_capability.py:101`, `skills/book-knowledge/tests/test_kg_capability.py:106`, `skills/book-knowledge/tests/test_kg_capability.py:107`.
   - Problem: the query joins `code-node -> code-claim-link -> claim`, but never touches `code-edge`. If `project_graphify` loaded nodes but zero edges, both capability tests still pass.
   - Evidence from live store probe:

     ```text
     cap_proposed= ([('alpha.py', 'clm-2026-000001'), ('beta.py', 'clm-2026-000002')], edge_count=4, claim_count=3)
     cap_empty_links= ([('alpha.py', 'clm-2026-000001'), ('beta.py', 'clm-2026-000002')], edge_count=0, claim_count=3)
     ```

   - Why it matters: the test is a genuine cross-store code-node/claim test, but it is not a full graphify-fusion acceptance test. A regression that drops every code edge would be caught by `test_project_graphify.py`, not by "THE deliverable" capability test.
   - Proposed fix: either add an assertion in `test_kg_capability.py` that the same store has the expected `code_edge` rows, or make the capability query traverse a real code edge before the code-claim link, e.g. module `contains` function plus module-to-claim link.
   - Must fix before merge: No, if `test_project_graphify.py` remains required; yes if this capability test is treated as the sole acceptance gate.

3. [MINOR] P4 plan self-review overclaims deferred recompute work.

   - Location: `docs/superpowers/plans/2026-06-16-homoiconic-kg-p4-graphify-fusion.md:39`, `docs/superpowers/plans/2026-06-16-homoiconic-kg-p4-graphify-fusion.md:57`, `docs/superpowers/plans/2026-06-16-homoiconic-kg-p4-graphify-fusion.md:64`.
   - Problem: P4.2 and P4.4 are unchecked, but the self-review says P4 implements "in-engine recompute" and that correctness is by "capability test + recompute-match".
   - Evidence: `rg --files -g "*graph*algo*" -g "kg_graph_algos.py" -g "*graphify*"` finds no `kg_graph_algos.py`; `rg -n "PageRank|Louvain|recompute"` finds only comments/plan text and rank/community-null assertions.
   - Why it matters: the code is honestly deferred, but the closeout text is not. A maintainer reading only the self-review could believe PageRank/Louvain recompute-match landed.
   - Proposed fix: change the self-review line to state P4.1 and P4.3 landed; P4.2 recompute-match and P4.4 CLI remain follow-on. Leave the checked/unchecked task boxes as they are.
   - Must fix before merge: Yes, documentation-only.

Claims-to-verify:

1. CONFIRMED, with edge-sensitivity caveat. Evidence: `test_kg_capability.py:55-61` projects claims and graphify into one `CozoStore`; `:65-82` loads `code-claim-link`; `:101-109` joins `code-node`, `code-claim-link`, and `claim`; `:113-118` asserts exact verified rows and near-miss exclusion. Probe mutation `proposed -> verified` changed output from 2 rows to 3:

   ```text
   cap_status3_verified= [('alpha.py', 'clm-2026-000001'), ('alpha.py', 'clm-2026-000003'), ('beta.py', 'clm-2026-000002')]
   ```

2. CONFIRMED. RDF/SPARQL path has no graphify code graph; P4 adds `code-node`, `code-edge`, and `code-claim-link` in Cozo schema at `kg-schema.edn:177`, `:193`, and `:214`. The result is not vacuous: exact non-empty pairs are asserted, and a zero-claim probe returned `[]`, which would fail the test.

3. CONFIRMED for same input and dict-key order independence. Probe:

   ```text
   two_run_equal= True
   reversed_key_equal= True
   ```

   The loader emits rows in JSON array order, not sorted order; that is deterministic for a fixed graph.json.

4. CONFIRMED. Necessary: Cozo `:put` keys on the first attr, and the P4 schema changed `code-edge` from `[:source-id ...]` to `[:id :source-id ...]` at `kg-schema.edn:193-195`; the plan documents the prior collapse at `...p4-graphify-fusion.md:37`. Safe at repo scale: fixture edge ids were unique:

   ```text
   ['edge-bf8d6aec03fb7b3e', 'edge-dcefe9e8bcbe1a35', 'edge-2a3f158325b9dff4', 'edge-99d27d096da8ca6a'] unique=True
   ```

   Residual risk: if graphify emits two distinct records with the same `(source,target,relation)` but different metadata, the current schema intentionally collapses them because metadata is not represented.

5. CONFIRMED. Whole-repo grep `rg -n "^\s*(import\s+pycozo|from\s+pycozo)\b"` returned only `skills\book-knowledge\scripts\cozo_store.py:150`; `project_graphify.py` has no pycozo import.

6. CONFIRMED. `test_kg_schema.py:22-38` includes the existing entities plus `code-claim-link`, and `test_kg_schema.py:69-72` enforces exact entity set. `code-edge` gained only the first `:id` attr at `kg-schema.edn:193-195`.

7. CONFIRMED in code, REFUTED in one doc sentence. No `kg_graph_algos.py`, no PageRank/Louvain implementation, no CLI beyond `project_graphify.main` at `project_graphify.py:94-104`. The P4.2/P4.4 task boxes are unchecked, but the plan self-review overclaims recompute; see finding 3.

## What I could not verify

- I did not verify against the real `C:/Users/charl/ProjectLegends/graphify-out/graph.json`; I audited the committed fixture and adversarial synthetic graph.json documents.
- I did not verify POSIX venv behavior; this run was Windows-only.
- I did not verify P4.2 PageRank/Louvain algorithm semantics because no implementation is present.
- I did not verify production code-to-claim link derivation because it is explicitly deferred; the P4 test loads explicit link rows.
- I did not mathematically prove SHA1-64 collision impossibility; I only confirmed no fixture collision and that collision risk is acceptable at repo scale.

## Deferred-work check

P4.2/P4.4 absence is clean in code: no `kg_graph_algos.py`, no PageRank/Louvain calls, no `recompute_code_graph`, and no sample CLI beyond the thin `project_graphify.py` main. `rank` and `community` are left null and asserted as such at `test_project_graphify.py:45-47`; no dangling population code exists.

The code-claim link semantics follow-on is honestly scoped in implementation comments: `kg-schema.edn:208-212` and `test_kg_capability.py:16-17` say production derivation from source files/symbol references is follow-on and that the current test uses explicit links. The one exception is the P4 plan self-review at line 64, which should be corrected per finding 3.
