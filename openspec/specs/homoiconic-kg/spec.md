# Capability: homoiconic-kg

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
- **unit normalization** — conversion of a `claim-quantity` to a canonical unit
  for its dimension (e.g. all lengths to metres) via the declared `claim-unit`, so
  two quantities are compared as numbers in one unit. *(S4)*
- **normal form** — the `claim-normal-form` row: the canonicalized
  subject/predicate/object triple a claim asserts, with quantities unit-normalized,
  against which exact contradiction is decided. *(S4)*
- **quantity clash** — two in-scope claims whose `claim-normal-form` share subject
  and predicate but carry incompatible normalized quantities (outside a declared
  tolerance). *(S4)*
- **interval inconsistency** — two `claim-time-interval` rows whose temporal
  relation violates a required one: disjoint where overlap is required, or
  overlapping where disjointness is required. *(S4)*
- **supersession chain** — the ordered `supersedes` links from a claim to the
  claims it replaces; **stale** when a superseded claim is still asserted as
  current, **invalid** when the chain is cyclic or names a missing claim. *(S4)*
- **paraphrastic residue** — a candidate contradiction pair that fails every
  symbolic check yet remains a candidate; routed to the external NLI seam. *(S4)*

## Requirements

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

### Requirement: REQ-KG-010 — Claim RDF path removed only after equivalence (State-driven)

The framework SHALL retain the claim-side RDF/SPARQL/SHACL stack while any
characterization fixture is not yet reproduced, and SHALL remove it only once
every fixture is reproduced (the cutover gate, P5). `rdflib` MAY remain for the
retained thesis-entailment trio and the `audit_taxonomy` RDFS taxonomy linter.

Rationale: deletion before equivalence would lose invariants the suite depends on;
the gate makes the big-bang reversible until proven.

#### Scenario: cutover is blocked while any fixture is unmatched

- **WHEN** the cutover check runs and any characterization fixture is not reproduced
- **THEN** the check fails and the claim-side RDF stack is not removed
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

### Requirement: REQ-KG-012 — SHACL shapes reproduced via EDN constraints (Ubiquitous)

The framework SHALL reauthor each shape and constraint in `assets/shapes.ttl` as a
booklogic `defconstraint` compiled by the pure EDN→CozoScript compiler to a Cozo
violation rule, whose conformance verdict and violation set are result-set equal to
`pyshacl`'s on the bermuda workspace and on a deliberately-violating fixture. The
covered constraints are the `ClaimShape` property constraints (`schema:text`
cardinality/datatype, the `tbf:status` `sh:in` enum, `tbf:confidence` datatype and
`0.0..1.0` range, `tbf:hasSourceSpan` minimum cardinality) and the two `sh:sparql`
constraints (verified claims must derive from a source-span; chapter sections must
cite only verified claims).

Rationale: result-set equality against a captured golden is the working definition
of a correct constraint port and the gate for retiring SHACL.

#### Scenario: each ported constraint matches the SHACL golden

- **WHEN** the EDN constraint suite runs over the bermuda workspace and over the violating fixture
- **THEN** its conformance verdict and the (focus-node, path, message) violation set are result-set equal to the captured `pyshacl` golden for the same input
- **AND** `tests/test_constraint_ports.py::test_constraints_match_shacl_golden` passes

### Requirement: REQ-KG-013 — `validate_shacl` public contract preserved (Ubiquitous)

The `validate_shacl(layout) -> ShaclReport` seam SHALL remain importable from
`scripts.validate_shacl` with an unchanged result shape (`conforms: bool`,
`violations: list[Violation(focus_node, path, message)]`, `text: str`), so that
`book-compose`'s `preflight.py`, `book_preflight.py`, and `build_release_bundle.py`
consume it without code change after its internals move from `pyshacl` to the Cozo
constraint path. Its internals SHALL reach the store through `cozo_store`, never
importing `pycozo` directly (REQ-KG-002b).

Rationale: the three cross-skill callers gate releases on `report.conforms`;
preserving the contract makes the engine swap invisible to them, exactly as
`cozo_store` makes the backend swap invisible to query callers.

#### Scenario: cross-skill callers are unchanged across the engine swap

- **WHEN** `validate_shacl` runs on the Cozo constraint path
- **THEN** it returns a `ShaclReport` with the same fields and the same `conforms` verdict the `pyshacl` path returned for that workspace
- **AND** `tests/test_validate_shacl.py::test_cozo_path_matches_contract` passes
- **AND** `tests/test_validate_shacl.py::test_callers_import_unchanged` asserts the three `book-compose` callers import and call it with no signature change

### Requirement: REQ-KG-014 — SHACL and consistency goldens precede their ports (State-driven)

In addition to REQ-KG-005, the framework SHALL hold committed golden fixtures for
the SHACL conformance/violation report and for the D9–D11 consistency defect set on
a deliberately-violating fixture (not only the bermuda workspace), and the
violating-fixture goldens SHALL be non-empty, while any SHACL or consistency port
PR is open.

Rationale: REQ-KG-005 already requires the bermuda goldens; this adds the
non-vacuity guard — a port that reproduces an empty golden proves nothing, so the
violating-fixture golden must fire — without restating REQ-KG-005's bermuda scope.

#### Scenario: the violating-fixture goldens exist and are non-empty

- **WHEN** the SHACL or consistency port PR is open
- **THEN** the SHACL-report and D9–D11 goldens for the violating fixture exist, are committed, and are non-empty
- **AND** `tests/test_characterization.py::test_violating_fixture_goldens_nonempty` passes

### Requirement: REQ-KG-015 — D9–D11 consistency reproduced via EDN→Cozo; pyDatalog retired (Ubiquitous)

The framework SHALL produce the D9 (orphan), D10 (transitive contradiction), and
D11 (invariant violation) defects — currently produced by `book-thesis`'s
`datalog_consistency` (pyDatalog over `consistency.dl`) — via a booklogic EDN→Cozo
consistency pass whose defect set is result-set equal to the captured golden.

Rationale: pyDatalog is the second Datalog engine the migration collapses into
Cozo; D9–D11 are the defects the QA gate depends on, so they must port with
equivalence before the dependency is removed.

#### Scenario: the EDN consistency pass matches the D9–D11 golden

- **WHEN** the EDN→Cozo consistency pass runs on the bermuda workspace and the violating fixture
- **THEN** its D9/D10/D11 defect set is result-set equal to the `datalog_consistency` golden for the same input
- **AND** `tests/test_consistency_ports.py::test_d9_d11_match_golden` passes

### Requirement: REQ-KG-015b — No pyDatalog after cutover (Unwanted)

No module SHALL import `pyDatalog` once the cutover gate (REQ-KG-018) passes. The
import scan that enforces this is owned by the cutover gate (REQ-KG-018), which
covers `rdflib`/`pyshacl`/`pyDatalog` together.

Rationale: separates the always-true equivalence obligation (REQ-KG-015) from the
state-gated removal of the engine; the single import-scan lives with the legacy
gate so there is one owner, not two.

#### Scenario: nothing imports pyDatalog after cutover

- **WHEN** the source tree is scanned after the cutover gate passes
- **THEN** no source module imports `pyDatalog`
- **AND** `tests/test_cutover_gate.py::test_no_legacy_import_after_cutover` passes

### Requirement: REQ-KG-016 — Thesis projects into Cozo (Event-driven)

The framework SHALL project `compile_thesis`'s thesis-node, sub-argument, and
invariant content into Cozo relations matching `kg-schema.edn` when the thesis→cozo
projection step runs, leaving the thesis YAML source unmodified, so the EDN
consistency pass (REQ-KG-015) reads thesis facts from Cozo rather than from
`thesis-triples.ttl`.

Rationale: D9–D11 join thesis structure against the claim ledger; the consistency
port needs the thesis side of that join inside the single store.

#### Scenario: thesis content lands in Cozo relations

- **WHEN** the thesis→cozo projector runs on a thesis fixture
- **THEN** Cozo holds the thesis-node/sub-argument/invariant rows matching `kg-schema.edn`, and the thesis YAML is byte-identical before and after
- **AND** `tests/test_thesis_projector.py::test_projects_thesis_nodes` passes

### Requirement: REQ-KG-017 — RDF↔Cozo divergences reconciled (Event-driven)

The framework SHALL resolve each of the three divergences documented inline in
`assets/kg-queries/*.edn` (`stale_after_source_refresh`'s structurally-dead SPARQL
join, `unsupported_claims`'s `wasDerivedFrom`-vs-source-span negation, and the
`project_graph` `wiki/wiki/` prefix + per-record `ccStatus` quirks) to one
canonical semantics before cutover, with the affected golden updated to that
semantics and the decision recorded in the change.

Rationale: the parallel-stack phase deliberately mirrored RDF quirks to prove
equivalence; the cutover must instead choose the intended behaviour so the
single-store result is correct, not bug-compatible.

#### Scenario: each divergence has a recorded canonical decision and an updated golden

- **WHEN** the cutover lands
- **THEN** each of the three divergences has a recorded canonical-semantics decision and its golden reflects that decision
- **AND** `tests/test_query_ports.py::test_all_eight_match_golden[query]` passes against the reconciled goldens

### Requirement: REQ-KG-018 — Legacy claim stack removed only behind the cutover gate (State-driven)

The framework SHALL retain the claim-side SPARQL/SHACL/pyDatalog stack,
`project_graph`'s RDF emit, `shapes.ttl`, and the `.rq` files while any
characterization fixture is unreproduced or any claim-side consumer still parses or
writes the RDF dataset, and SHALL remove them — including the
`pyshacl`/`pyDatalog` dependency pins across `book-knowledge`, `book-compose`, and
`book-thesis` — only once the cutover gate passes (every fixture reproduced, every
claim-side consumer on the Cozo path, `KG_BACKEND` defaulting to `cozo`). `rdflib`
SHALL remain allowed only for the thesis-entailment trio and `audit_taxonomy`.
This gate supersedes REQ-KG-010's narrower claim-side RDF/SPARQL/SHACL gate.

Rationale: deletion before equivalence would lose invariants the suite depends on
and break the cross-skill callers; the gate makes the big-bang reversible until
proven.

#### Scenario: cutover is blocked while any fixture is unmatched or any consumer touches RDF

- **WHEN** the cutover check runs and any characterization fixture is unreproduced or any claim-side source module still parses or writes the RDF dataset or imports `pyshacl`/`pyDatalog`, or imports `rdflib` outside the retained allowlist
- **THEN** the check fails and the legacy claim stack is not removed
- **AND** `tests/test_cutover_gate.py::test_blocks_until_all_fixtures_pass` and `::test_no_legacy_import_after_cutover` pass

### Requirement: REQ-KG-019 — Remaining claim RDF-dataset reader ported to Cozo (Ubiquitous)

The framework SHALL reauthor `query_chapter_evidence.py` (book-compose) to read
its claim facts through `cozo_store`, with output result-set equal to its captured
golden on the bermuda workspace. `audit_taxonomy.py` (book-knowledge) SHALL remain
an explicitly retained `rdflib` RDFS taxonomy linter outside the claim-ledger
cutover.

Rationale: without this, REQ-KG-018's gate deadlocks — it blocks cutover while any
claim-side consumer reads RDF, but REQ-KG-006 ports only the eight queries, leaving
`query_chapter_evidence.py` permanently on the RDF path.

#### Scenario: the remaining claim reader matches its golden on the Cozo path

- **WHEN** `query_chapter_evidence` runs on the bermuda workspace through `cozo_store`
- **THEN** its output is result-set equal to its captured golden, and it does not parse the TriG dataset
- **AND** `skills/book-compose/tests/test_query_chapter_evidence.py::test_query_chapter_evidence_reads_ledger_not_trig` passes

### Requirement: REQ-KG-020 — Transition matrix derives its state set from the single EDN source (Ubiquitous)

The framework SHALL derive the state set used by `claim_validator.VALID_TRANSITIONS`
from the same single EDN status source as REQ-KG-009, such that the transition
matrix cannot name a status absent from that source, and adding a status to the
source surfaces it to the validator.

Rationale: `VALID_TRANSITIONS` is a fifth, independently-edited copy of the status
vocabulary (the transition graph, not just the enum list), which REQ-KG-009/009b do
not cover; once SHACL's `sh:in` is deleted, this is the remaining drift source.

#### Scenario: the transition matrix cannot name an unknown status

- **WHEN** the transition matrix is built and a status not in the single EDN source is referenced
- **THEN** the build fails (or the matrix is derived so the status cannot appear)
- **AND** `tests/test_status_enum_single_source.py::test_transition_matrix_uses_single_source` passes

### Requirement: REQ-KG-021 — Normalized helper relations declared (Ubiquitous)

The schema SHALL declare the `claim-quantity`, `claim-unit`,
`claim-time-interval`, and `claim-normal-form` helper relations in
`kg-schema.edn`, each with its attributes, and the projector SHALL emit them for
in-scope claims.

Rationale: the symbolic rules decide contradiction over normalized facts, not raw
prose; these four relations are the normalized substrate, declared in the one EDN
source of truth (REQ-KG-001) so the compiler and projectors read them.

#### Scenario: schema declares the four helper relations

- **WHEN** `kg-schema.edn` is parsed
- **THEN** `claim-quantity`, `claim-unit`, `claim-time-interval`, and `claim-normal-form` are each present with a non-empty attribute list
- **AND** the projector emits rows for them on a claim carrying a quantity, a unit, and a time interval
- **AND** `tests/test_contradiction_workbench.py::test_schema_declares_helper_relations` passes

### Requirement: REQ-KG-022 — Quantity clash is a hard contradiction (Event-driven)

When two in-scope claims share subject and predicate in their `claim-normal-form`
but assert incompatible quantities after unit normalization, the system SHALL mark
a hard contradiction between them.

Rationale: "30 km" and "18 mi" agree; "30 km" and "300 km" do not. Comparing in a
canonical unit catches the clash the lexical detector misses.

#### Scenario: incompatible quantities clash after unit normalization

- **WHEN** the pass runs on two claims asserting the same subject/predicate with quantities that disagree once converted to a canonical unit
- **THEN** the two claims are marked a hard contradiction
- **AND** two claims whose quantities agree after conversion (different units, same magnitude) are not marked
- **AND** `tests/test_contradiction_workbench.py::test_quantity_clash_after_unit_normalization` passes

### Requirement: REQ-KG-023 — Interval inconsistency is flagged (Event-driven)

When two claims' `claim-time-interval` rows are inconsistent — disjoint where the
predicate requires overlap, or overlapping where it requires disjointness — the
system SHALL flag an interval inconsistency between them.

Rationale: temporal contradictions ("active 1910–1915" vs "active 1920–1925" for a
predicate requiring overlap) are invisible to lexical and untimed symbolic checks.

#### Scenario: inconsistent time intervals are flagged

- **WHEN** the pass runs on two claims whose required temporal relation is violated by their intervals
- **THEN** an interval inconsistency is flagged for that pair
- **AND** two claims whose intervals satisfy the required relation are not flagged
- **AND** `tests/test_contradiction_workbench.py::test_interval_inconsistency_flagged` passes

### Requirement: REQ-KG-024 — Stale or invalid supersession chain is flagged (Event-driven)

When a supersession chain is stale (a superseded claim still asserted as current)
or invalid (cyclic, or naming a missing claim), the system SHALL flag it.

Rationale: a supersession chain that is stale or malformed silently leaves
retracted claims in play; the writer must not ground a sentence on a claim a later
claim replaced.

#### Scenario: stale and invalid chains are flagged

- **WHEN** the pass runs on a ledger where a superseded claim is still asserted as current
- **THEN** that chain is flagged stale
- **AND** a cyclic or missing-target chain is flagged invalid
- **AND** a well-formed chain with the superseded claim retired is not flagged
- **AND** `tests/test_contradiction_workbench.py::test_stale_or_invalid_supersession_flagged` passes

### Requirement: REQ-KG-025 — Symbolic checks are deterministic (Ubiquitous)

The symbolic contradiction checks (quantity clash, interval inconsistency,
supersession) SHALL be a deterministic function of a ledger snapshot, producing
result-set-equal defect sets for the same snapshot across runs.

Rationale: determinism is what makes the symbolic surface golden-able and lets S0
gate on it; it also separates the deterministic core from the non-deterministic NLI
seam (REQ-KG-026).

#### Scenario: same snapshot yields the same defect set

- **WHEN** the symbolic checks run twice on one frozen snapshot
- **THEN** the two defect sets are result-set equal under canonical ordering
- **AND** `tests/test_contradiction_workbench.py::test_symbolic_checks_deterministic` passes

### Requirement: REQ-KG-026 — Paraphrastic residue routes to the NLI seam (Optional)

Where a candidate contradiction pair fails every symbolic check yet remains a
candidate, the system SHALL route it to the external NLI seam as paraphrastic
residue, and SHALL NOT route a pair already resolved by a symbolic check.

Rationale: the symbolic checks own everything decidable by normalization; only what
survives them is genuine paraphrastic residue worth a model call, keeping the
non-deterministic seam off the deterministic path.

#### Scenario: only symbolic-residue pairs reach the seam

- **WHEN** the pass runs on a candidate pair that no symbolic check resolves
- **THEN** that pair is routed to the NLI seam as paraphrastic residue
- **AND** a pair already marked by a symbolic check is not routed to the seam
- **AND** `tests/test_contradiction_workbench.py::test_residue_routes_to_nli_seam` passes

### Requirement: REQ-KG-027 — Residue survives an unavailable seam (Unwanted)

If the NLI seam is unavailable, then the symbolic checks SHALL still run to
completion and each residue pair SHALL be marked unresolved rather than dropped.

Rationale: the deterministic core must never depend on the optional seam; an
offline or failed seam degrades to a marked-unresolved residue, not silent loss of
a candidate contradiction.

#### Scenario: unavailable seam leaves residue marked unresolved

- **WHEN** the pass runs with the NLI seam stubbed unavailable
- **THEN** the symbolic defect set is produced unchanged
- **AND** each residue pair is marked unresolved rather than discarded
- **AND** `tests/test_contradiction_workbench.py::test_residue_unresolved_when_seam_down` passes
