# Capability: homoiconic-kg (delta for kg-contradiction-workbench)

This change ADDS requirements REQ-KG-012..018 to the existing `homoiconic-kg`
capability. The numbering continues that capability's REQ-KG sequence (the landed
change reached REQ-KG-011); no existing requirement is renumbered or restated.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **unit normalization** — conversion of a `claim-quantity` to a canonical unit
  for its dimension (e.g. all lengths to metres) via the declared `claim-unit`, so
  two quantities are compared as numbers in one unit.
- **normal form** — the `claim-normal-form` row: the canonicalized
  subject/predicate/object triple a claim asserts, with quantities unit-normalized
  and predicates mapped to a canonical name, against which exact contradiction is
  decided.
- **quantity clash** — two in-scope claims whose `claim-normal-form` share subject
  and predicate but carry incompatible normalized quantities (outside a declared
  tolerance).
- **interval inconsistency** — two `claim-time-interval` rows whose temporal
  relation violates a required one: disjoint where the predicate requires overlap,
  or overlapping where it requires disjointness.
- **supersession chain** — the ordered `supersedes` links from a claim to the
  claims it replaces; **stale** when a superseded claim is still asserted as
  current, **invalid** when the chain is cyclic or names a missing claim.
- **paraphrastic residue** — a candidate contradiction pair that fails every
  symbolic check yet remains a candidate, contradicting (if at all) only under a
  meaning-preserving rephrase; the residue routed to the external NLI seam.

## ADDED Requirements

### Requirement: REQ-KG-012 — Normalized helper relations declared (Ubiquitous)

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

### Requirement: REQ-KG-013 — Quantity clash is a hard contradiction (Event-driven)

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

### Requirement: REQ-KG-014 — Interval inconsistency is flagged (Event-driven)

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

### Requirement: REQ-KG-015 — Stale or invalid supersession chain is flagged (Event-driven)

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

### Requirement: REQ-KG-016 — Symbolic checks are deterministic (Ubiquitous)

The symbolic contradiction checks (quantity clash, interval inconsistency,
supersession) SHALL be a deterministic function of a ledger snapshot, producing
result-set-equal defect sets for the same snapshot across runs.

Rationale: determinism is what makes the symbolic surface golden-able and lets S0
gate on it; it also separates the deterministic core from the non-deterministic NLI
seam (REQ-KG-017).

#### Scenario: same snapshot yields the same defect set

- **WHEN** the symbolic checks run twice on one frozen snapshot
- **THEN** the two defect sets are result-set equal under canonical ordering
- **AND** `tests/test_contradiction_workbench.py::test_symbolic_checks_deterministic` passes

### Requirement: REQ-KG-017 — Paraphrastic residue routes to the NLI seam (Optional)

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

### Requirement: REQ-KG-018 — Residue survives an unavailable seam (Unwanted)

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
