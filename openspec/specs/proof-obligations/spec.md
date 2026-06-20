# Capability: proof-obligations

The proof-obligations capability makes proof obligations first-class, replayable KG entities that gate math/science prose: a requires-proof claim opens a pending obligation discharged or refuted by an injected checker (z3/cvc5/lean/units/stats-report) with committed, replayable artifacts, and the writer asserts a claim as verified only once discharged. First defined by the `kg-proof-obligations` change (archived).

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **proof-obligation** — a `proof-obligation` row binding a `statement` to a
  `linked-claim`, carrying a `checker-kind`, `status`, `assumptions`,
  `artifact-path`, `countermodel-path`, `checked-at`, and `normal-form`.
- **checker-kind** — the verifier a `proof-obligation` routes to: one of `z3`,
  `cvc5`, `lean`, `units`, `stats-report`.
- **discharged** — an obligation status set when its checker proves the
  `statement`; a `verification-artifact` exists for it.
- **refuted** — an obligation status set when its checker disproves the
  `statement`; a `countermodel-path` exists for it.
- **waived** — an obligation status set by an explicit author decision to not
  require discharge; the waiver is recorded against the obligation.
- **verification-artifact** — a record of one checker run: its `artifact-path`,
  `checked-at`, and the obligation it discharges.
- **countermodel** — the witness a checker emits when it refutes an obligation,
  stored at `countermodel-path`.
- **gated sentence** — a final-prose sentence asserting a claim whose obligation
  the writer passes were required to respect.
- **scientific-claim-check** — the seam validating a scientific claim's units,
  uncertainty qualifiers, evidence type, and statistical-reporting norms, emitting
  guideline failures as machine-readable obligations.

## Requirements

### Requirement: REQ-PROOF-001 — Proof-obligation schema (Ubiquitous)

The schema SHALL declare a `proof-obligation` entity, a `verification-artifact`
record, and a `requires-proof` relation, with the `proof-obligation` carrying
`statement`, `linked-claim`, `checker-kind`, `status`, `assumptions`,
`artifact-path`, `countermodel-path`, `checked-at`, and `normal-form`.

Rationale: making proof obligations first-class KG entities is the whole of move
#6; nothing downstream gates or replays without them in the schema.

#### Scenario: schema declares the obligation entities and relation

- **WHEN** the schema is loaded
- **THEN** `proof-obligation`, `verification-artifact`, and `requires-proof` are declared with the `proof-obligation` attributes above
- **AND** a `proof-obligation` row missing `checker-kind` or `status` is rejected
- **AND** `tests/test_proof_obligations.py::test_schema_declares_obligation_entities` passes

### Requirement: REQ-PROOF-002 — Obligation creation (Event-driven)

When a claim is marked `requires-proof`, the system SHALL create a
`proof-obligation` for it with a `checker-kind` and `status` `pending`.

Rationale: a delicate claim must hold an open obligation before any writer pass
sees it, so the gate has something to wait on.

#### Scenario: requiring proof opens a pending obligation

- **WHEN** a claim is marked `requires-proof`
- **THEN** exactly one `proof-obligation` exists for that claim with a `checker-kind` and `status` `pending`
- **AND** `tests/test_proof_obligations.py::test_requires_proof_opens_pending_obligation` passes

### Requirement: REQ-PROOF-003 — Discharge records an artifact (Event-driven)

When a checker proves an obligation, the system SHALL record a
`verification-artifact` (with `artifact-path` and `checked-at`) and SHALL set the
obligation's `status` to `discharged`.

Rationale: the discharge must be replayable evidence in the graph, not a transient
verifier exit code.

#### Scenario: a proven obligation becomes discharged with an artifact

- **WHEN** a checker proves a pending obligation
- **THEN** the obligation's status is `discharged`
- **AND** a `verification-artifact` for it exists with `artifact-path` and `checked-at` set
- **AND** `tests/test_proof_obligations.py::test_discharge_records_artifact` passes

### Requirement: REQ-PROOF-004 — Refutation records a countermodel (Event-driven)

When a checker disproves an obligation, the system SHALL record the
`countermodel-path` and SHALL set the obligation's `status` to `refuted`.

Rationale: a refutation is as load-bearing as a discharge; the countermodel is the
witness the author needs to correct or retract the claim.

#### Scenario: a disproven obligation becomes refuted with a countermodel

- **WHEN** a checker disproves a pending obligation
- **THEN** the obligation's status is `refuted`
- **AND** its `countermodel-path` points at the emitted countermodel
- **AND** `tests/test_proof_obligations.py::test_refutation_records_countermodel` passes

### Requirement: REQ-PROOF-005 — Writer gating on undischarged claims (State-driven)

While a claim's obligation is undischarged, the math/science writer passes SHALL
NOT assert that claim as verified.

Rationale: a claim is assertable-as-verified only once its obligation is
discharged; an open obligation must hold the writer back.

#### Scenario: undischarged claim is not asserted as verified

- **WHEN** the writer passes run on a chapter whose claim has a `pending` obligation
- **THEN** no produced sentence asserts that claim as verified
- **AND** the claim is omitted or stated non-canonically rather than asserted
- **AND** `tests/test_proof_obligations.py::test_undischarged_claim_not_asserted` passes

### Requirement: REQ-PROOF-006 — Conjectural assertion under a waiver (Optional)

Where an obligation is explicitly waived, the writer MAY state the claim as
conjectural with the waiver noted.

Rationale: not every delicate claim can be discharged; an explicit waiver lets the
writer voice it as a conjecture rather than suppress it silently.

#### Scenario: waived obligation permits a noted conjectural statement

- **WHEN** the writer passes run on a claim whose obligation is `waived`
- **THEN** the claim may appear stated as conjectural with the waiver noted on the sentence
- **AND** it is not asserted as verified
- **AND** `tests/test_proof_obligations.py::test_waived_claim_stated_conjectural` passes

### Requirement: REQ-PROOF-007 — Scientific-claim-check flagging (Event-driven)

When a scientific claim lacks required units, uncertainty qualifiers, or
statistical reporting, the `scientific-claim-check` seam SHALL flag it (for
example, `statistical-claim-underreported`).

Rationale: statistical-reporting norms (EQUATOR/PRISMA) are checkable; storing the
failures as obligations makes scientific rigor a gate rather than a hope.

#### Scenario: an underreported scientific claim is flagged

- **WHEN** the seam checks a scientific claim missing units, an uncertainty qualifier, or required statistical reporting
- **THEN** the seam emits a flag such as `statistical-claim-underreported` as a machine-readable obligation
- **AND** a claim carrying units, an uncertainty qualifier, and the required reporting is not flagged
- **AND** `tests/test_proof_obligations.py::test_scientific_claim_check_flags_underreported` passes

### Requirement: REQ-PROOF-008 — Offline, replayable checker runs (Ubiquitous)

Checker runs SHALL be offline and replayable with their artifacts committed, and
z3/cvc5/lean SHALL be invoked behind a seam.

Rationale: the suite's discipline is offline determinism; a verifier reached
directly would make discharges non-replayable and the graph non-auditable.

#### Scenario: a checker run replays from committed artifacts

- **WHEN** the dispatch routes an obligation to z3, cvc5, or lean
- **THEN** the verifier is invoked through the seam with no network access
- **AND** re-running the obligation reproduces the same status from the committed artifact
- **AND** `tests/test_proof_obligations.py::test_checker_runs_offline_replayable` passes

### Requirement: REQ-PROOF-009 — Gated-sentence escape is a hard failure (Unwanted)

If a sentence asserting an undischarged gated claim reaches final prose, then the
QA gate SHALL fail.

Rationale: a gated sentence escaping to final prose defeats the entire obligation
mechanism; `gated-sentence-escape` must be a hard failure, not a warning.

#### Scenario: an escaped gated sentence fails the QA gate

- **WHEN** final prose contains a sentence asserting a claim whose obligation is undischarged and unwaived
- **THEN** the QA gate fails with `gated-sentence-escape`
- **AND** the failure is hard, not advisory
- **AND** `tests/test_proof_obligations.py::test_gated_sentence_escape_hard_fails` passes
