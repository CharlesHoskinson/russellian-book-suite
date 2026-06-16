# Homoiconic KG — P0 + P1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the homoiconic-front / Cozo-back knowledge-graph store in `book-knowledge` and prove the round-trip by reproducing all 8 existing SPARQL competency queries as booklogic EDN→Cozo — with the RDF stack still running in parallel (no deletion).

**Architecture:** A single EDN schema (`kg-schema.edn`) drives a Cozo store reached through one Python seam (`cozo_store`, backed by `pycozo`). A pure EDN→CozoScript compiler lowers booklogic queries. A `ledger→cozo` projector loads latest-per-id verified claims. Characterization golden fixtures freeze current SPARQL output first; each ported query must be result-set equal to its golden before P5 cutover. Spec: `openspec/changes/homoiconic-kg-edn-front-cozo-back/` (REQ-KG-001..011).

**Tech Stack:** Python 3.13, `pycozo[embedded]` (Cozo Datalog), existing `rdflib` (kept parallel), `edn_format` for EDN parsing on the Python side, pytest.

---

## File structure

| File | Responsibility |
|---|---|
| `skills/book-knowledge/assets/kg-schema.edn` (new) | The one EDN graph contract: entities, attributes, relations (REQ-KG-001) |
| `skills/book-knowledge/scripts/cozo_store.py` (new) | The single Python↔store seam: `query`/`load`, relation creation from schema, backend-agnostic (REQ-KG-002, 007, 011) |
| `skills/book-knowledge/scripts/booklogic_kg.py` (new) | Pure EDN→CozoScript compiler (REQ-KG-003) |
| `skills/book-knowledge/scripts/project_ledger_cozo.py` (new) | `ledger→cozo` projector (REQ-KG-004) |
| `skills/book-knowledge/assets/kg-queries/*.edn` (new) | The 8 competency queries authored as booklogic EDN (REQ-KG-006) |
| `skills/book-knowledge/tests/golden/kg/*.json` (new) | Characterization fixtures (REQ-KG-005) |
| `skills/book-knowledge/tests/test_*` (new) | One test module per requirement |
| `skills/book-knowledge/scripts/run_competency_queries.py` (modify) | Add EDN→Cozo path behind a flag (REQ-KG-006 P1.5) |
| `skills/book-knowledge/pyproject.toml` (modify) | Add `pycozo[embedded]` + `edn_format` deps |

Run all tests from `skills/book-knowledge` with `.venv/Scripts/python.exe -m pytest`.

---

## P0 — Stand up the store

### Task P0.1: Characterization harness (REQ-KG-005)

**Files:**
- Create: `skills/book-knowledge/tests/golden/kg/.gitkeep`
- Create: `skills/book-knowledge/scripts/capture_characterization.py`
- Test: `skills/book-knowledge/tests/test_characterization.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_characterization.py
from pathlib import Path
import pytest

GOLDEN = Path(__file__).parent / "golden" / "kg"
REQUIRED = [  # the 8 query names + the SHACL + datalog fixtures
    "unsupported_claims", "chapter_evidence_coverage", "orphan_wiki_pages",
    "stale_after_source_refresh", "contradiction_scan",
    "contested-rebuttal-window", "posterior-floor", "rebuttal-presence",
]

@pytest.mark.parametrize("name", REQUIRED)
def test_required_goldens_present(name):
    assert (GOLDEN / f"{name}.json").exists(), f"missing golden for {name}"
```

- [ ] **Step 2: Run it — expect FAIL** (`...::test_required_goldens_present` — files absent).

- [ ] **Step 3: Implement `capture_characterization.py`** — run each `.rq` via the existing `run_competency_queries` machinery on the bermuda workspace (`examples/bermuda-manual`) and write each result set (list of binding dicts, sorted by a canonical key) to `tests/golden/kg/<name>.json`.

```python
# scripts/capture_characterization.py
import json, sys
from pathlib import Path
from scripts.run_competency_queries import discover_queries, _load_dataset
from scripts.workspace import WorkspaceLayout

def capture(workspace: Path, out_dir: Path) -> None:
    layout = WorkspaceLayout(workspace)
    ds = _load_dataset(layout)
    out_dir.mkdir(parents=True, exist_ok=True)
    for _cls, name, path in discover_queries(Path("assets")):
        rows = [{str(k): str(v) for k, v in r.asdict().items()}
                for r in ds.query(path.read_text(encoding="utf-8"))]
        rows.sort(key=lambda d: json.dumps(d, sort_keys=True))
        (out_dir / f"{name}.json").write_text(
            json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")

if __name__ == "__main__":
    capture(Path(sys.argv[1]), Path(sys.argv[2]))
```

- [ ] **Step 4: Generate the goldens** on the bermuda workspace, then run the test — expect PASS.

Run: `.venv/Scripts/python.exe -m scripts.capture_characterization ../../examples/bermuda-manual tests/golden/kg` then `pytest tests/test_characterization.py -q`.

- [ ] **Step 5: Commit** `git add … && git commit -m "kg(P0.1): characterization goldens for the 8 SPARQL queries (REQ-KG-005)"`

### Task P0.2: kg-schema.edn (REQ-KG-001)

**Files:**
- Create: `skills/book-knowledge/assets/kg-schema.edn`
- Test: `skills/book-knowledge/tests/test_kg_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kg_schema.py
from pathlib import Path
import edn_format

SCHEMA = Path("assets/kg-schema.edn")
ENTITIES = {"claim", "source-span", "thesis-node", "sub-argument",
            "wiki-page", "code-node", "code-edge", "community"}

def _load():
    return edn_format.loads(SCHEMA.read_text(encoding="utf-8"))

def test_schema_declares_all_entities_attrs_relations():
    doc = _load()
    ents = {edn_format.dumps(k).lstrip(":") for k in doc[edn_format.Keyword("entities")]}
    assert ENTITIES <= ents
    for _name, spec in doc[edn_format.Keyword("entities")].items():
        assert spec[edn_format.Keyword("attrs")], "entity needs attrs"
```

- [ ] **Step 2: Run it — expect FAIL** (file absent).

- [ ] **Step 3: Author `kg-schema.edn`** — one map: `{:entities {:claim {:attrs [:id :status :canonical-text :claim-type :confidence] :relations [[:has-source :source-span]]} :source-span {:attrs [:doc-id :locator-text] :relations []} :thesis-node {...} :sub-argument {...} :wiki-page {...} :code-node {:attrs [:id :label :rank :community] :relations [[:edge :code-edge]]} :code-edge {:attrs [:source-id :target-id :relationship :weight]} :community {:attrs [:id :members]}}}`. Fill each `:attrs` from the JSON-Schema record + graphify `graph.json` node/edge shape.

- [ ] **Step 4: Run the test — expect PASS.**

- [ ] **Step 5: Commit** `kg(P0.2): unified EDN graph schema (REQ-KG-001)`

### Task P0.3: cozo_store seam over pycozo (REQ-KG-002, 011)

**Files:**
- Modify: `skills/book-knowledge/pyproject.toml` (add `pycozo[embedded]>=0.7,<1.0`, `edn_format>=0.7,<1.0`)
- Create: `skills/book-knowledge/scripts/cozo_store.py`
- Test: `skills/book-knowledge/tests/test_cozo_store_contract.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cozo_store_contract.py
from pathlib import Path
from scripts.cozo_store import CozoStore

def test_query_returns_rows():
    s = CozoStore.in_memory(schema_path=Path("assets/kg-schema.edn"))
    s.load("claim", [{"id": "clm-1", "status": "verified",
                      "canonical_text": "x", "claim_type": "fact", "confidence": 0.9}])
    rows = s.query('?[id] := *claim{id, status}, status == "verified"')
    assert rows == [["clm-1"]]

def test_relations_conform_to_schema():
    s = CozoStore.in_memory(schema_path=Path("assets/kg-schema.edn"))
    rels = s.relations()
    assert "claim" in rels and "source-span" in rels
    assert "not_in_schema" not in rels
```

- [ ] **Step 2: Run — expect FAIL** (module absent).

- [ ] **Step 3: Implement `cozo_store.py`** — a `CozoStore` wrapping `pycozo.Client('mem')`; `in_memory(schema_path)` reads `kg-schema.edn` and runs a `:create` per entity (columns from `:attrs`); `load(relation, rows)` does a `:put`; `query(cozoscript)` returns `result['rows']`; `relations()` lists created relations. **This module is the only place that imports `pycozo`.**

- [ ] **Step 4: Run — expect PASS.** (If `pycozo[embedded]` fails to build on the runner, mark P0.3 blocked and resolve the wheel before proceeding — see Risk in design.md.)

- [ ] **Step 5: Commit** `kg(P0.3): cozo_store seam over pycozo + schema→relation creation (REQ-KG-002, 011)`

### Task P0.4: No-bypass + stub-backend contract (REQ-KG-002b, 007)

**Files:** Modify `tests/test_cozo_store_contract.py`; Modify `cozo_store.py` (extract a `Backend` protocol + `CozoBackend` + `StubBackend`).

- [ ] **Step 1: Write the failing tests**

```python
def test_no_module_bypasses_seam():
    import subprocess, sys
    hits = subprocess.run([sys.executable, "-c",
        "import pathlib,re; "
        "print([str(p) for p in pathlib.Path('scripts').rglob('*.py') "
        "if p.name!='cozo_store.py' and re.search(r'import pycozo', p.read_text(encoding='utf-8'))])"],
        capture_output=True, text=True).stdout.strip()
    assert hits == "[]", f"modules import pycozo directly: {hits}"

def test_stub_backend_satisfies_contract():
    from scripts.cozo_store import CozoStore, StubBackend
    s = CozoStore(backend=StubBackend(), schema_path=Path("assets/kg-schema.edn"))
    s.load("claim", [{"id": "clm-1", "status": "verified"}])
    assert s.query('?[id] := *claim{id, status}, status == "verified"') == [["clm-1"]]
```

- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement** the `Backend` protocol (`create`, `put`, `run`), `CozoBackend` (pycozo), and a small in-memory `StubBackend` that satisfies the same contract for the queries P0/P1 exercise.
- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `kg(P0.4): backend-agnostic seam + no-bypass guard (REQ-KG-002b, 007)`

### Task P0.5: EDN→CozoScript compiler skeleton (REQ-KG-003)

**Files:** Create `scripts/booklogic_kg.py`; Test `tests/test_booklogic_kg_compile.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_booklogic_kg_compile.py
from pathlib import Path
from scripts.booklogic_kg import compile_query

SCHEMA = Path("assets/kg-schema.edn")

def test_defquery_golden():
    edn = '(defquery :verified-ids :find [?id] :where [[?c :claim/id ?id] [?c :claim/status "verified"]])'
    out = compile_query(edn, SCHEMA)
    assert out == '?[id] := *claim{id, status}, status == "verified"'
    assert compile_query(edn, SCHEMA) == out  # byte-identical

def test_compile_without_store():
    edn = '(defquery :verified-ids :find [?id] :where [[?c :claim/id ?id] [?c :claim/status "verified"]])'
    assert isinstance(compile_query(edn, SCHEMA), str)  # no store needed

def test_undeclared_entity_raises():
    import pytest
    edn = '(defquery :q :find [?x] :where [[?c :ghost/id ?x]])'
    with pytest.raises(ValueError, match="ghost"):
        compile_query(edn, SCHEMA)
```

- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement `compile_query(edn, schema_path) -> str`** — parse the EDN `defquery`, validate each `:where` triple's entity/attr against `kg-schema.edn`, and emit CozoScript. Start with the minimal subset the 8 queries need (single-relation match, equality filter, `not exists`/negation, joins on shared vars). Pure function, no I/O beyond reading the schema once.
- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `kg(P0.5): pure EDN→CozoScript compiler skeleton (REQ-KG-003)`

### Task P0.6: ledger→cozo projector (REQ-KG-004)

**Files:** Create `scripts/project_ledger_cozo.py`; Test `tests/test_ledger_projector.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ledger_projector.py
from pathlib import Path
from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ledger import append_claim
from scripts.cozo_store import CozoStore
from scripts.project_ledger_cozo import project_ledger

def test_projects_latest_verified_claims(tmp_path):
    ws = init_workspace(tmp_path / "book"); layout = WorkspaceLayout(ws)
    append_claim(layout, {"claim_id": "clm-2026-000001", "canonical_text": "x",
        "status": "verified", "claim_type": "fact", "confidence": 0.9,
        "source_spans": [{"doc_id": "d", "locator_text": "loc"}],
        "created_at": "2026-05-11T00:00:00Z"})
    before = layout.ledger.read_text(encoding="utf-8")
    store = CozoStore.in_memory(schema_path=Path("assets/kg-schema.edn"))
    project_ledger(layout, store)
    assert store.query('?[id] := *claim{id, status}, status=="verified"') == [["clm-2026-000001"]]
    assert layout.ledger.read_text(encoding="utf-8") == before  # ledger untouched
```

- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement `project_ledger(layout, store)`** — read the ledger via `io_utils.read_jsonl` + `latest_per("claim_id")`, keep `status == "verified"`, `store.load("claim", ...)` and `store.load("source-span", ...)`. No writes to the ledger.
- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `kg(P0.6): ledger→cozo projector, latest-per-id verified (REQ-KG-004)`

### Task P0.7: Determinism pin (REQ-KG-008)

**Files:** Test `tests/test_determinism.py`.

- [ ] **Step 1: Write the failing test** — project + run one query twice on the bermuda workspace; assert the projected rows are byte-identical and the canonically-sorted result sets are byte-identical between two fresh stores.
- [ ] **Step 2: Run — expect FAIL** (until ordering is canonicalised in `cozo_store.query`/projector).
- [ ] **Step 3: Implement** canonical sorting of rows in `cozo_store.query` results and stable ordering in the projector load.
- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `kg(P0.7): determinism pin for projector + query (REQ-KG-008)`

---

## P1 — Port the 8 competency queries (REQ-KG-006)

### Task P1.1: Port `unsupported_claims` (worked example)

**Files:** Create `assets/kg-queries/unsupported_claims.edn`; Test `tests/test_query_ports.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_query_ports.py
import json
from pathlib import Path
from scripts.cozo_store import CozoStore
from scripts.booklogic_kg import compile_query
from scripts.project_ledger_cozo import project_ledger
from scripts.workspace import WorkspaceLayout

BERMUDA = Path("../../examples/bermuda-manual")
GOLDEN = Path(__file__).parent / "golden" / "kg"

def _run(name):
    store = CozoStore.in_memory(schema_path=Path("assets/kg-schema.edn"))
    project_ledger(WorkspaceLayout(BERMUDA), store)
    edn = (Path("assets/kg-queries") / f"{name}.edn").read_text(encoding="utf-8")
    rows = store.query(compile_query(edn, Path("assets/kg-schema.edn")))
    return sorted(rows)

def test_unsupported_claims_matches_golden():
    golden = json.loads((GOLDEN / "unsupported_claims.json").read_text(encoding="utf-8"))
    expected = sorted([list(r.values()) for r in golden])
    assert _run("unsupported_claims") == expected
```

- [ ] **Step 2: Run — expect FAIL** (query EDN absent).
- [ ] **Step 3: Author `unsupported_claims.edn`** — booklogic EDN for "verified claims with no source": `(defquery :unsupported-claims :find [?c] :where [[?c :claim/status "verified"]] :not [[?c :claim/has-source ?s]])`. Target CozoScript: `?[c] := *claim{id: c, status}, status == "verified", not *source_span{claim_id: c}`. Adjust the projector/schema so a verified claim with zero source-spans is detectable; iterate until the test matches the golden.
- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `kg(P1.1): port unsupported_claims to EDN→Cozo, golden-matched (REQ-KG-006)`

### Task P1.2–P1.4: Port the remaining seven queries (same pattern, parametrized)

**Files:** Create `assets/kg-queries/{chapter_evidence_coverage,orphan_wiki_pages,stale_after_source_refresh,contradiction_scan,contested-rebuttal-window,posterior-floor,rebuttal-presence}.edn`; Modify `tests/test_query_ports.py`.

- [ ] **Step 1: Add the parametrized gate test**

```python
import pytest
ALL = ["unsupported_claims", "chapter_evidence_coverage", "orphan_wiki_pages",
       "stale_after_source_refresh", "contradiction_scan",
       "contested-rebuttal-window", "posterior-floor", "rebuttal-presence"]

@pytest.mark.parametrize("query", ALL)
def test_all_eight_match_golden(query):
    golden = json.loads((GOLDEN / f"{query}.json").read_text(encoding="utf-8"))
    expected = sorted([list(r.values()) for r in golden])
    assert _run(query) == expected
```

- [ ] **Step 2: Run — expect FAIL** for the seven not-yet-authored.
- [ ] **Step 3: Author each `.edn`** one at a time, reading the corresponding `.rq` for intent, extending the compiler's supported clause set only as a query needs it (e.g. aggregation for coverage, threshold filters for defeasible). Commit per query.
- [ ] **Step 4: Run — expect PASS** for all eight parameters.
- [ ] **Step 5: Commit per query** `kg(P1.x): port <query> to EDN→Cozo (REQ-KG-006)`

### Task P1.5: Wire run_competency_queries to the EDN→Cozo path behind a flag

**Files:** Modify `scripts/run_competency_queries.py`; Test `tests/test_run_competency_queries.py`.

- [ ] **Step 1: Write the failing test** — with the env flag `KG_BACKEND=cozo`, `run_competency_queries` returns the same fire/defect set it returns under the default rdflib path (compare on the bermuda workspace).
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement** a backend switch: default = rdflib/SPARQL (unchanged); `KG_BACKEND=cozo` routes through `cozo_store` + compiled EDN. Both paths produce the same shape.
- [ ] **Step 4: Run — expect PASS** (both backends green against the golden harness).
- [ ] **Step 5: Commit** `kg(P1.5): run_competency_queries EDN→Cozo path behind KG_BACKEND flag (REQ-KG-006)`

---

## Self-review

- **Spec coverage:** REQ-KG-001→P0.2; 002/011→P0.3; 002b/007→P0.4; 003→P0.5; 004→P0.6; 005→P0.1; 008→P0.7; 006→P1.1–P1.5. REQ-KG-009/009b/010 are P2/P5 (out of this plan, by design). No P0+P1 gap.
- **Placeholder scan:** the only deliberately-discovered content is exact CozoScript per query — guarded by the golden tests (write golden → implement EDN→Cozo until result-set equal), which is the intended TDD loop, not a placeholder.
- **Type consistency:** `CozoStore.in_memory(schema_path=)`, `.load(relation, rows)`, `.query(cozoscript) -> rows`, `compile_query(edn, schema_path) -> str`, `project_ledger(layout, store)` used consistently across tasks.
- **Risk gate:** P0.3 is the pivot — if `pycozo[embedded]` will not build on a CI runner, resolve the wheel before P0.4+ (the seam's `StubBackend` lets P0.4/P0.5/compiler tasks proceed in parallel meanwhile).
