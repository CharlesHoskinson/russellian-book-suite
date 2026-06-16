# Capability delta: homoiconic-kg — change: homoiconic-kg-edn-front-cozo-back

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **byte-identical** — octet-for-octet equal serialization. Used for compiler
  output and projected relations.
- **result-set equal** — equal as an unordered multiset of rows after a canonical
  sort (CozoScript and SPARQL do not guarantee row order). Used for query ports.
- **reproduced** — the fixture's golden-match test passes.
- **latest-per-id verified** — the most recent ledger record for a claim id whose
  status is `verified` (per `latest_per`).

## ADDED Requirements

### Requirement: REQ-KG-001 — Unified EDN schema (Ubiquitous)

The framework SHALL define the unified knowledge-graph schema as a single EDN
document (`kg-schema.edn`) that declares all eight entities (`claim`,
`source-span`, `thesis-node`, `sub-argument`, `wiki-page`, `code-node`,
`code-edge`, `community`) with their attributes and relations.

Rationale: one EDN contract is the homoiconic source of truth the projectors and
the compiler read; it is distinct from the JSON-Schema record contract, which
still guards ledger-write shape.

#### Scenario: schema declares the full entity set with attributes and relations

- **WHEN** `kg-schema.edn` is parsed
- **THEN** all eight named entities are present, each with a non-empty attribute list, and the inter-entity relations are declared
- **AND** `tests/test_kg_schema.py::test_schema_declares_all_entities_attrs_relations` passes

#### Scenario: record contract is unchanged

- **WHEN** a claim is written to the ledger
- **THEN** validation still uses the JSON-Schema record contract, not `kg-schema.edn`

### Requirement: REQ-KG-002 — Single Cozo store behind one Python seam (Ubiquitous)

The framework SHALL expose the knowledge graph through one Python seam module
(`cozo_store`) backed by an embedded Cozo store via `pycozo`, presenting
`query(edn) -> rows` and `load(relation, rows)`.

Rationale: a single seam is the contract-tested boundary that keeps the backend
swappable (REQ-KG-007) and consolidates the two Datalog engines into one.

#### Scenario: consumers query through the seam

- **WHEN** a consumer calls `cozo_store.query(edn)`
- **THEN** it receives rows from the embedded Cozo store
- **AND** `tests/test_cozo_store_contract.py::test_query_returns_rows` passes

### Requirement: REQ-KG-002b — No direct backend access (Unwanted)

No module other than `cozo_store` SHALL import `pycozo`. CozoScript *text* MAY be
produced by the pure EDN→CozoScript compiler (REQ-KG-003); only the `pycozo`
engine dependency is isolated to the seam, since that — not the query language —
is what the Cozo→Asami swap must replace.

Rationale: routing the backend *engine* through the seam is what makes the Cozo→
Asami swap a one-module change; the compiler emitting CozoScript strings does not
bind the system to Cozo (a different backend gets a different compile target).

#### Scenario: nothing imports pycozo except the seam

- **WHEN** the source tree is scanned for `import pycozo` / `from pycozo`
- **THEN** only `cozo_store` matches
- **AND** `tests/test_cozo_store_contract.py::test_no_module_bypasses_seam` passes

### Requirement: REQ-KG-003 — Pure EDN→CozoScript compiler (Ubiquitous)

The booklogic→CozoScript compiler SHALL be a pure function that, given an EDN
query or constraint and `kg-schema.edn`, returns byte-identical CozoScript for the
same input and performs no store I/O.

Rationale: a pure compiler is unit-testable in isolation and is the layer where
homoiconicity lives.

#### Scenario: EDN query compiles to byte-identical CozoScript

- **WHEN** the compiler is given a fixed EDN `defquery` twice
- **THEN** it returns the same CozoScript string both times, matching the golden
- **AND** `tests/test_booklogic_kg_compile.py::test_defquery_golden` passes

#### Scenario: compiler runs with no store bound

- **WHEN** the compiler is invoked with no Cozo instance available
- **THEN** it still returns CozoScript (no I/O)
- **AND** `tests/test_booklogic_kg_compile.py::test_compile_without_store` passes

#### Scenario: reference to an undeclared entity is rejected

- **WHEN** an EDN query references an entity absent from `kg-schema.edn`
- **THEN** the compiler raises a clear error naming the entity

### Requirement: REQ-KG-004 — Ledger projects into Cozo (Event-driven)

The framework SHALL load every latest-per-id non-superseded claim (the same claim
set `project_graph` emits) and its source-spans into Cozo relations matching
`kg-schema.edn` when the `ledger→cozo` projection step runs, and SHALL leave the
ledger file unmodified. The `claim` rows carry their `status`, so each query
applies its own status filter (matching the SPARQL it replaces).

Rationale: the projector replaces `project_graph`'s RDF emit, so it must hold the
same node set the SPARQL queries saw (all non-superseded, not verified-only) —
otherwise the no-status-filter queries (`contradiction_scan`, `posterior-floor`)
would diverge from their goldens on any fixture with non-verified claims.

#### Scenario: bermuda ledger projects to latest-per-id non-superseded claim rows

- **WHEN** the `ledger→cozo` projector runs on the bermuda workspace
- **THEN** Cozo holds exactly one `claim` row per latest-per-id non-superseded claim, each with its `status` and source-spans
- **AND** the ledger file is byte-identical before and after
- **AND** `tests/test_ledger_projector.py::test_projects_latest_nonsuperseded_claims` passes

### Requirement: REQ-KG-005 — Characterization fixtures precede a port (Event-driven)

The framework SHALL already hold a committed golden fixture — for the named query,
the SHACL conformance report, or the D9–D11 defect set — before the PR that ports
that behaviour to EDN→Cozo lands.

Rationale: the fixtures freeze current RDF/SPARQL/SHACL/pyDatalog behaviour so the
big-bang replace is guarded by equivalence, not assertion.

#### Scenario: a query-port PR finds its golden already present

- **WHEN** a query-port PR is opened
- **THEN** `tests/golden/kg/<query>.json` for that query already exists and is committed
- **AND** `tests/test_characterization.py::test_required_goldens_present` passes for all 8 queries, the SHACL report, and the D9–D11 set

### Requirement: REQ-KG-006 — Each SPARQL query reproduced via EDN→Cozo (Ubiquitous)

Each of the eight competency/coverage/defeasible queries SHALL be authored as a
booklogic EDN query whose output is result-set equal to that query's golden
fixture on the bermuda workspace.

Rationale: result-set equality is the working definition of a correct port and the
gate for retiring SPARQL.

#### Scenario: every one of the eight matches its golden

- **WHEN** the parametrized port suite runs over the eight query names
- **THEN** each EDN→Cozo query's output is result-set equal to its golden fixture
- **AND** `tests/test_query_ports.py::test_all_eight_match_golden[query]` passes for all eight parameters

### Requirement: REQ-KG-007 — Backend is swappable behind the seam (Ubiquitous)

The `cozo_store` seam SHALL present a backend-agnostic interface such that
replacing the Cozo backend with another engine requires no change to any consumer
module.

Rationale: it de-risks Cozo's maintenance staleness and keeps the pure-EDN store
(north star) reachable.

#### Scenario: a stub backend satisfies the same contract

- **WHEN** the contract test runs the seam against an in-memory stub backend
- **THEN** the same `query`/`load` calls and assertions pass unchanged
- **AND** no consumer module imports a backend symbol (shares `test_no_module_bypasses_seam`)
- **AND** `tests/test_cozo_store_contract.py::test_stub_backend_satisfies_contract` passes

### Requirement: REQ-KG-008 — Deterministic load and query (Ubiquitous)

Graph load and query SHALL be deterministic: the same inputs SHALL produce
byte-identical projected relations and, after canonical ordering, byte-identical
result sets across runs.

Rationale: determinism is required for golden-fixture comparison and reproducible
QA gating; the canonical-ordering clause reconciles with REQ-KG-006's set-equality.

#### Scenario: two runs match

- **WHEN** the projector and a query run twice on the same workspace
- **THEN** the projected rows are byte-identical and the canonically-ordered result sets are byte-identical between runs
- **AND** `tests/test_determinism.py::test_project_and_query_stable` passes

### Requirement: REQ-KG-009 — Status enum has one EDN source (Ubiquitous)

The framework SHALL derive both the schema's status enumeration and the
status-validity constraint from a single EDN value holding the five states
(`proposed`, `verified`, `disputed`, `superseded`, `refuted`).

Rationale: a single source removes the documented off-by-one foot-gun where the
SHACL `sh:in` list and the JSON-Schema enum diverge silently.

#### Scenario: editing the one source updates both views

- **WHEN** a status value is added to the single EDN enum source
- **THEN** both the schema view and the validity constraint accept it with no second edit
- **AND** `tests/test_status_enum_single_source.py::test_one_source_feeds_both` passes

### Requirement: REQ-KG-009b — No duplicate enum copy (Unwanted)

The framework SHALL NOT maintain a second, independently-edited copy of the status
enumeration.

Rationale: any second copy reintroduces the drift REQ-KG-009 removes.

#### Scenario: only one enum source exists

- **WHEN** the source tree is scanned for the status-value list
- **THEN** the canonical EDN source is the only authored copy (others are derived)
- **AND** `tests/test_status_enum_single_source.py::test_no_second_enum_copy` passes

### Requirement: REQ-KG-010 — RDF removed only after equivalence (State-driven)

The framework SHALL retain the `rdflib`/SPARQL/SHACL stack while any
characterization fixture is not yet reproduced, and SHALL remove it only once
every fixture is reproduced (the cutover gate, P5).

Rationale: deletion before equivalence would lose invariants the suite depends on;
the gate makes the big-bang reversible until proven.

#### Scenario: cutover is blocked while any fixture is unmatched

- **WHEN** the cutover check runs and any characterization fixture is not reproduced
- **THEN** the check fails and the RDF stack is not removed
- **AND** `tests/test_cutover_gate.py::test_blocks_until_all_fixtures_pass` passes

### Requirement: REQ-KG-011 — Store relations conform to the schema (Ubiquitous)

`cozo_store` SHALL create every Cozo relation from `kg-schema.edn`, and a relation
absent from `kg-schema.edn` SHALL NOT exist in the store.

Rationale: this is the missing link between REQ-KG-001 (schema) and REQ-KG-004
(rows land) — without it nothing checks that relation *shapes* match the schema.

#### Scenario: store schema matches the EDN schema

- **WHEN** `cozo_store` initializes a store from `kg-schema.edn`
- **THEN** every declared entity has a corresponding relation with matching columns, and no extra relation exists
- **AND** `tests/test_cozo_store_contract.py::test_relations_conform_to_schema` passes
