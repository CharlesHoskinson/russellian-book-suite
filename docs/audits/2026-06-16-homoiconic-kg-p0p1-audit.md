# Homoiconic-KG P0+P1 Audit

Date: 2026-06-16. Commit audited: `9eac18e` (`9eac18eb8407c4bc8c98d52487a727af0d4c251b`).

> **Resolution (2026-06-16).** All four findings fixed, TDD, on branch
> `fix/2026-06-16-homoiconic-kg-audit` (commits `57929db` F1, `9a2a09b` F2,
> `95ee54f` F3, `09390fd` F4): F1 — added `CozoStore.query_edn` as the EDN
> consumer API (raw `query` kept internal); F2 — `__init__` raises on relations
> absent from `kg-schema.edn`, test strengthened to equality + rogue-relation
> regression; F3 — `Client(..., dataframe=False)` (no pandas traceback); F4 —
> no-bypass scan widened to the whole skill tree. Suite **243 passed**; bermuda
> competency identical on both backends. The three documented RDF↔Cozo divergences
> remain correctly deferred to P5.

Overall verdict: READY-WITH-FIXES. The EDN query ports are not vacuous: all seven empty Bermuda goldens have synthetic-fire tests, the non-empty chapter coverage golden has 10 rows, and the full `skills/book-knowledge` suite passed in a temporary clone. However, P0 is not cleanly spec-compliant: the public store seam exposes CozoScript instead of `query(edn)`, and schema-absent relations are not rejected. Test run: `C:\Users\charl\russellian-book-suite\skills\book-knowledge\.venv\Scripts\python.exe -m pytest -q` from temp clone `...\rbs-audit-9eac18e\repo\skills\book-knowledge` -> `240 passed in 3.55s`.

## Verdict summary

Severity counts for actionable findings: Critical 0, Important 2, Minor 2.

Category counts: Real bug 4; Documented-known divergences correctly deferred to P5 3; Non-issue/verified-correct checks 11.

Additional command evidence:

- `git rev-parse HEAD` -> `9eac18eb8407c4bc8c98d52487a727af0d4c251b`.
- Whole-repo pycozo grep: `rg -n "^\s*(import\s+pycozo|from\s+pycozo)\b"` -> only `skills/book-knowledge/scripts/cozo_store.py:150`.
- Golden row counts: `chapter_evidence_coverage: 10`; the other seven query goldens are `0`.
- Direct Bermuda runner counts matched on both backends: default rdflib and `KG_BACKEND=cozo` each reported chapter coverage `10 rows`, all other queries `0 rows`, `warnings: 0`.

## Spec coverage

| REQ-id | implementing file | verifying test | satisfied? | note |
|---|---|---|---|---|
| REQ-KG-001 | `skills/book-knowledge/assets/kg-schema.edn:21` | `skills/book-knowledge/tests/test_kg_schema.py:68` | Y | Schema declares the required entities plus query-support relations; attrs/relations are checked. |
| REQ-KG-002 | `skills/book-knowledge/scripts/cozo_store.py:396` | `skills/book-knowledge/tests/test_cozo_store_contract.py:28` | partial | Real Cozo store exists, but public `query` takes CozoScript, not EDN; see F1. |
| REQ-KG-002b | `skills/book-knowledge/scripts/cozo_store.py:150` | `skills/book-knowledge/tests/test_cozo_store_contract.py:76` | partial | Whole-repo grep is clean, but the committed test scans only `scripts/`; see F4. |
| REQ-KG-003 | `skills/book-knowledge/scripts/booklogic_kg.py:312` | `skills/book-knowledge/tests/test_booklogic_kg_compile.py:29` | Y | Compiler is pure, deterministic, validates unknown entities/attrs, lowers joins/negation/filters/aggregates. |
| REQ-KG-004 | `skills/book-knowledge/scripts/project_ledger_cozo.py:204` | `skills/book-knowledge/tests/test_ledger_projector.py:38` | Y | Latest-per-id non-superseded claims and spans project; ledger byte-identity is asserted. |
| REQ-KG-005 | `skills/book-knowledge/scripts/capture_characterization.py:57` | `skills/book-knowledge/tests/test_characterization.py:35` | Y | All eight goldens are tracked by `git ls-files`; capture refuses an empty dataset. |
| REQ-KG-006 | `skills/book-knowledge/assets/kg-queries/*.edn` | `skills/book-knowledge/tests/test_query_ports.py:63` and synthetic-fire tests through `:550` | Y | All eight ports match goldens and have non-vacuous fire tests where needed. |
| REQ-KG-007 | `skills/book-knowledge/scripts/cozo_store.py:337` | `skills/book-knowledge/tests/test_cozo_store_contract.py:93` | partial | Backend protocol hides pycozo types, but consumer-facing CozoScript leaks through `query`; see F1. |
| REQ-KG-008 | `skills/book-knowledge/scripts/project_ledger_cozo.py:257` | `skills/book-knowledge/tests/test_determinism.py:107` and `:122` | Y | Stable projection and canonical result-set tests pass. |
| REQ-KG-009 | `openspec/changes/homoiconic-kg-edn-front-cozo-back/tasks.md:42` | none | deferred | Correctly left for P2; not falsely claimed done. |
| REQ-KG-009b | `openspec/changes/homoiconic-kg-edn-front-cozo-back/specs/homoiconic-kg/spec.md:195` | none | deferred | Correctly left for P2; no done claim found. |
| REQ-KG-010 | `openspec/changes/homoiconic-kg-edn-front-cozo-back/tasks.md:56` | none | deferred | Correctly left for P5; RDF/SPARQL/SHACL remain present. |
| REQ-KG-011 | `skills/book-knowledge/scripts/cozo_store.py:366` | `skills/book-knowledge/tests/test_cozo_store_contract.py:41` | partial | Creates declared relations, but does not reject pre-existing extra relations; see F2. |

## Findings

### F1 [IMPORTANT][REAL BUG] Public store seam is CozoScript, not EDN

**Location**: `openspec/changes/homoiconic-kg-edn-front-cozo-back/specs/homoiconic-kg/spec.md:45`, `openspec/changes/homoiconic-kg-edn-front-cozo-back/design.md:42`, `skills/book-knowledge/scripts/cozo_store.py:396`, `skills/book-knowledge/scripts/run_competency_queries.py:108`, `skills/book-knowledge/scripts/run_competency_queries.py:118`, `skills/book-knowledge/scripts/run_competency_queries.py:119`.

**Evidence**: The spec requires `query(edn) -> rows` and says callers should never see CozoScript. The implementation is `def query(self, cozoscript: str)` and forwards directly to `Backend.run`. The Cozo competency path imports `compile_query`, compiles EDN in `run_competency_queries`, then calls `store.query(script)`. Tests also assert direct CozoScript calls, e.g. `test_cozo_store_contract.py:37`.

**Why it matters**: The compiler target leaks into consumers. Replacing Cozo with another backend is not a one-module swap if consumers already compile and pass CozoScript.

**Recommended fix**: Make the public seam accept EDN. Move the `compile_query(edn, schema)` call behind `CozoStore.query(edn_text)` or add `query_edn` as the only public consumer API, keep raw script execution private/internal, and update `run_competency_queries.py:118-119` plus contract tests to pass EDN to the seam.

### F2 [IMPORTANT][REAL BUG] `CozoStore` does not enforce "no extra relation exists"

**Location**: `openspec/changes/homoiconic-kg-edn-front-cozo-back/specs/homoiconic-kg/spec.md:223`, `skills/book-knowledge/scripts/cozo_store.py:366`, `skills/book-knowledge/scripts/cozo_store.py:367`, `skills/book-knowledge/tests/test_cozo_store_contract.py:46`, `skills/book-knowledge/tests/test_cozo_store_contract.py:49`.

**Evidence**: `CozoStore.__init__` reads existing relations and creates missing schema relations, but never checks `existing - declared`. The test asserts `expected <= relations` plus two spot negatives, not equality. Probe in temp clone:

```text
backend = StubBackend()
backend.create('rogue_relation', ['id'], {})
store = CozoStore(backend=backend, schema_path=schema)
print('rogue_relation' in store.relations()) -> True
```

**Why it matters**: REQ-KG-011 says a relation absent from `kg-schema.edn` shall not exist. A stale or rogue relation can survive store initialization and become a false dependency for later queries/constraints.

**Recommended fix**: In `CozoStore.__init__`, compute `declared = set(self._relations)` and `extra = existing - declared`; raise `ValueError(f"relations absent from kg-schema.edn: {sorted(extra)}")` before creating missing relations. Strengthen `test_relations_conform_to_schema` to assert equality for a fresh store and add a `StubBackend` test seeded with `rogue_relation` that must fail.

### F3 [MINOR][REAL BUG] Cozo backend emits a pandas traceback on successful CLI runs

**Location**: `skills/book-knowledge/scripts/cozo_store.py:150`, `skills/book-knowledge/scripts/cozo_store.py:152`.

**Evidence**: Direct command in temp clone:

```text
$env:KG_BACKEND='cozo'; ...python.exe -m scripts.run_competency_queries ..\..\examples\bermuda-manual
...
warnings: 0 defeasible fire(s)
`pandas` feature was requested, but pandas is not installed
Traceback ... ModuleNotFoundError: No module named 'pandas'
```

`inspect.signature(pycozo.client.Client.__init__)` reports `dataframe=True` by default. Probe `Client('mem','','', dataframe=False); run('?[x] <- [[1]]')` returned `[[1]]` without the traceback.

**Why it matters**: The command exits 0, but the stderr traceback makes a successful Cozo run look broken and can pollute CI/report logs.

**Recommended fix**: Change `client = Client("mem", "", "")` to `client = Client("mem", "", "", dataframe=False)` in `CozoBackend.__init__`, and add a small smoke test that constructs `CozoStore.in_memory` without emitting a pandas traceback when pandas is absent.

### F4 [MINOR][REAL BUG] The pycozo isolation test does not scan the source tree it claims to scan

**Location**: `openspec/changes/homoiconic-kg-edn-front-cozo-back/specs/homoiconic-kg/spec.md:69`, `skills/book-knowledge/tests/test_cozo_store_contract.py:18`, `skills/book-knowledge/tests/test_cozo_store_contract.py:85`.

**Evidence**: The requirement says the source tree is scanned. The test defines `SCRIPTS_DIR = ... / "scripts"` and loops over `SCRIPTS_DIR.rglob("*.py")`. My whole-repo grep is clean today, but the committed test would miss a future `pycozo` import in `skill_api.py`, tests, sibling package code, or any other Python file outside `scripts/`.

**Why it matters**: This is the exact seam regression REQ-KG-002b is meant to prevent; the test can go green while the repository violates the requirement.

**Recommended fix**: Set the scan root to the skill root or repo root, skip only `.venv`, cache/build dirs, and `cozo_store.py`, then assert no `import pycozo` / `from pycozo` matches anywhere else.

## Oracle integrity

| query | golden rows | empty golden? | synthetic-fire test? | independently re-derived empty as legitimate? |
|---|---:|---|---|---|
| `chapter_evidence_coverage` | 10 | N | Y, distinct-count synthetic at `test_query_ports.py:122` and `:168` | N/A; non-empty golden. |
| `unsupported_claims` | 0 | Y | Y, sourceless verified claim at `test_query_ports.py:69` | Y. Ledger/RDF probe: `projected_claims=14 verified=14`, `unsupported_by_ledger=[]`, `unsupported_by_rdf=[]`, `derived_refs=0`. |
| `stale_after_source_refresh` | 0 | Y | Y, refreshed-source synthetic at `test_query_ports.py:550` | Documented-known, not a silent oracle. Probe: `wasDerivedFrom_source_targets=14`, `targets_with_dateCreated=0`, `bare_uri_dateCreated_matches=14`; Cozo doc-id semantics still returns empty on Bermuda because source and claim dates are equal. |
| `contradiction_scan` | 0 | Y | Y, directional conflict synthetic at `test_query_ports.py:195` | Y. Ledger probe: `conflicts_by_ledger=[]`. |
| `orphan_wiki_pages` | 0 | Y | Y, orphan/reference pair at `test_query_ports.py:252` | Y for Bermuda: `wiki_dir_exists=False wiki_md_count=0`. |
| `posterior-floor` | 0 | Y | Y, sub-floor/pinned synthetic at `test_query_ports.py:335` | Y. Probe: `posterior_projected_count=10 min=0.4298874999999999`, `posterior_floor_by_ledger=[]`; non-vacuity asserted at `test_query_ports.py:329`. |
| `rebuttal-presence` | 0 | Y | Y, open/addressed/axiom synthetic at `test_query_ports.py:409` | Y. Probe: 18 counter-claim records, 9 ids, every id has `open` and `addressed`; no load-bearing exposed row returned. |
| `contested-rebuttal-window` | 0 | Y | Y, disputed chapter-support synthetic at `test_query_ports.py:478` | Y for Bermuda: all 14 projected claims are verified; no disputed claim binds the positive body. |

No query is relying only on an empty golden. The stale-source empty is empty for a broken RDF join, but that divergence is documented in the EDN file and P5 task list and has a synthetic fire test proving the Cozo port can return rows.

## RDF↔Cozo faithfulness

| item | faithful? | evidence |
|---|---|---|
| Claim node set | Y | RDF uses `latest_per(...).values()` and skips only `status == "superseded"` at `project_graph.py:38-39`; Cozo uses `latest_per(read_jsonl(...), "claim_id")` and the same skip at `project_ledger_cozo.py:214` and `:227`. |
| Source spans | Y | RDF emits source-span URI, `prov:wasDerivedFrom`, and `tbf:hasSourceSpan` for each span at `project_graph.py:54-58`; Cozo creates span rows with `claim_id`, `doc_id`, and optional `wiki_page_id` at `project_ledger_cozo.py:257-274`. |
| Claim -> chapter | Y | RDF emits `tbf:supportsChapter` and chapter type at `project_graph.py:63-66`; Cozo loads `claim-chapter`/`chapter` rows at `project_ledger_cozo.py:239` and `:316-317`. |
| Conflicts | Y | RDF emits directional `tbf:conflictsWith` at `project_graph.py:88-90`; Cozo loads directional `claim-conflict` rows at `project_ledger_cozo.py:249` and `:318`. |
| Counter-claims | Y for current RDF semantics | RDF iterates every counter-claim record and emits `ccStatus` at `project_graph.py:92-96`; Cozo preserves distinct status history at `project_ledger_cozo.py:289-306` and documents the set behavior at `kg-schema.edn:89-107`. |
| Wiki pages | Y, including quirk | RDF mints `BASE/wiki/<rel-to-root>` at `project_graph.py:99-104`; Cozo mirrors that doubled `wiki/wiki/` path in `_wiki_page_uri` at `project_ledger_cozo.py:90-99`. |
| Sources | Divergent by design for stale query | RDF puts `schema:dateCreated` on bare source URIs at `project_graph.py:107-118`, while claim `wasDerivedFrom` points to fragment span URIs at `project_graph.py:54-58`; Cozo joins by `doc_id` via `source-span/doc-id` -> `source/id` in `stale_after_source_refresh.edn`. |

Documented divergences:

- `stale_after_source_refresh`: real divergence, adequately documented at `skills/book-knowledge/assets/kg-queries/stale_after_source_refresh.edn:17-29` and deferred in `tasks.md:61-63`. Deferral to P5 is correct because the Cozo port intentionally fixes a structurally dead RDF join, and the synthetic test at `test_query_ports.py:550` proves it fires.
- `unsupported_claims`: real divergence, adequately documented at `skills/book-knowledge/assets/kg-queries/unsupported_claims.edn:16-22` and deferred in `tasks.md:64-65`. Deferral is acceptable because Bermuda has `derived_refs=0`, so the golden is not masking current data.
- `wiki/wiki` prefix and counter-claim no-dedup: real project_graph quirks, documented in `tasks.md:66-68`, `project_ledger_cozo.py:90-99`, `project_ledger_cozo.py:278-306`, and `kg-schema.edn:89-107`. Correctly deferred to P5 as canonical-semantics cleanup.

## Confirmed-correct

- Full book-knowledge suite passes in a temp clone with the project venv: `240 passed`.
- Default competency path remains rdflib; `KG_BACKEND=cozo` switches paths and `test_run_competency_queries.py:354` spies that `_load_dataset` is not called.
- Whole-repo pycozo import grep is clean today: only `cozo_store.py:150`.
- `CozoBackend.put` parameterizes loaded row data with `$rows` at `cozo_store.py:174-176`; ledger values are not string-interpolated into `:put`.
- Compiler lowers renamed find vars and shared-var joins; real Cozo execution tests are at `test_booklogic_kg_compile.py:159-166` and `:190-198`.
- Compiler lowers threaded negation safely and rejects unsafe negation at `booklogic_kg.py:234`; tests cover execution at `test_booklogic_kg_compile.py:266-277`.
- Compiler lowers `count-distinct` to `count_unique` at `booklogic_kg.py:105` and `:402`; chapter coverage returns 10 rows on Bermuda.
- Ordered filters add `!is_null` guards, including var-vs-var comparisons, at `booklogic_kg.py:295-306`; tests cover literal and var-vs-var cases.
- Typed Float/Int/Bool columns are declared from schema and compare correctly; tests at `test_cozo_store_contract.py:64-72` and `test_ledger_projector.py:130-137`.
- Empty-by-design relations are justified and explicit: `chapter-wiki-ref` at `project_ledger_cozo.py:322-324`, `rebuttal-window-ok` at `:326-330`.
- Malformed compiler probes returned clear `ValueError`s for missing `:find`, unsafe negation, and bad filter arity; invalid EDN raises `EDNDecodeError: EOF Reached`.

## Recommended fix order

1. Fix F1: make the public store seam accept EDN and keep CozoScript behind the seam.
2. Fix F2: reject schema-absent pre-existing relations and strengthen the conformance test to equality plus a rogue-relation regression.
3. Fix F3: instantiate `pycozo.Client(..., dataframe=False)` and add a no-pandas smoke assertion.
4. Fix F4: widen `test_no_module_bypasses_seam` to the skill/repo source tree with explicit cache/venv exclusions.
5. After those fixes, rerun `python -m pytest -q` and direct `KG_BACKEND=cozo`/default competency commands on Bermuda.
6. Leave the three documented RDF/Cozo divergences deferred to P5 unless product semantics are being decided now.
