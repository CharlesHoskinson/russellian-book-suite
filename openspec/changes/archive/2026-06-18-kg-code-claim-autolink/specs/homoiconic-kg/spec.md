# Capability: homoiconic-kg (delta for kg-code-claim-autolink)

This change EXTENDS the `homoiconic-kg` capability. It ADDS requirements
REQ-KG-035 through REQ-KG-040; no existing requirement is changed or renumbered.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **link-evidence** — a `link-evidence` row recording why a code↔claim link was
  proposed: its `kind`, a `score`, the `witness` that fired it, and its
  `provenance`. Evidence is stored for every candidate, canonical or not.
- **file-path link** — a `code-claim-link` of `kind` `file-path`, materialized
  when a claim's `source.file` matches a `code-node` module path.
- **exact-symbol link** — a `code-claim-link` of `kind` `exact-symbol`,
  materialized when a claim mention resolves to a symbol present in `code-node`
  reached by a CONTAINS/USES trail over `code-edge`.
- **canonical link** — a `code-claim-link` row promoted to the asserted graph,
  consumed by downstream projectors; only deterministic or thresholded-reviewed
  candidates qualify.
- **witness** — the concrete graph fact that fired a signal: the matched module
  path for `file-path`, or the resolved symbol plus the CONTAINS/USES trail for
  `exact-symbol`.

## ADDED Requirements

### Requirement: REQ-KG-035 — Link-evidence relation declared (Ubiquitous)

The schema SHALL declare a `link-evidence` relation carrying `kind`, `score`,
`witness`, and `provenance`, such that every proposed code↔claim link has a
corresponding evidence row.

Rationale: derived links must be auditable; the evidence relation is what makes a
canonical link justifiable and a rejected candidate inspectable rather than lost.

#### Scenario: schema declares link-evidence with its four fields

- **WHEN** `kg-schema.edn` is parsed
- **THEN** a `link-evidence` relation is present with `kind`, `score`, `witness`, and `provenance` attributes
- **AND** `tests/test_code_claim_autolink.py::test_schema_declares_link_evidence` passes

### Requirement: REQ-KG-036 — File-path links materialized from module-path match (Event-driven)

When a claim's `source.file` matches a `code-node` module path, the system SHALL
materialize a `code-claim-link` of `kind` `file-path` between that claim and the
matched `code-node`, and SHALL store the supporting `link-evidence` row.

Rationale: a claim whose source file is a module in the code graph is anchored to
that module by construction; the filename is a deterministic, replayable witness.

#### Scenario: source-file match yields a file-path link plus evidence

- **WHEN** the linker runs on a claim whose `source.file` equals a `code-node` module path
- **THEN** a `code-claim-link` of `kind` `file-path` exists between that claim and the `code-node`
- **AND** a `link-evidence` row records `kind` `file-path` with the matched module path as `witness`
- **AND** `tests/test_code_claim_autolink.py::test_file_path_link_materialized` passes

### Requirement: REQ-KG-037 — Exact-symbol links materialized via CONTAINS/USES trail (Event-driven)

When a claim mentions a symbol resolvable to a `code-node` reached by a
CONTAINS/USES trail over `code-edge`, the system SHALL materialize a
`code-claim-link` of `kind` `exact-symbol` between that claim and the resolved
`code-node`, and SHALL store the supporting `link-evidence` row.

Rationale: an exact symbol with a structural trail through the code graph is a
deterministic anchor; storing the trail as `witness` makes the link replayable.

#### Scenario: exact symbol with a containment/use trail yields an exact-symbol link

- **WHEN** the linker runs on a claim mentioning a symbol present in `code-node` reached by a CONTAINS/USES trail
- **THEN** a `code-claim-link` of `kind` `exact-symbol` exists between that claim and the resolved `code-node`
- **AND** a `link-evidence` row records `kind` `exact-symbol` with the resolved symbol and trail as `witness`
- **AND** `tests/test_code_claim_autolink.py::test_exact_symbol_link_materialized` passes

### Requirement: REQ-KG-038 — Only deterministic or reviewed links are canonical (Ubiquitous)

The system SHALL promote to canonical only links that are deterministic or
thresholded-and-reviewed; lower-confidence candidates SHALL be stored as
`link-evidence` and SHALL NOT appear as canonical `code-claim-link` rows.

Rationale: canonical links feed the writer's software grounding; admitting only
deterministic or reviewed links keeps that grounding trustworthy while preserving
weaker signals for the S9 ranker.

#### Scenario: low-confidence candidate stays evidence, not canonical

- **WHEN** the linker produces a deterministic candidate and a lower-confidence candidate for one claim
- **THEN** only the deterministic candidate becomes a canonical `code-claim-link`
- **AND** the lower-confidence candidate exists only as a `link-evidence` row
- **AND** `tests/test_code_claim_autolink.py::test_only_deterministic_canonical` passes

### Requirement: REQ-KG-039 — Deterministic linker over a snapshot (Ubiquitous)

The linker SHALL be a deterministic function of a graph snapshot, producing
result-set-equal canonical links and `link-evidence` rows for the same snapshot.

Rationale: determinism is the precondition for golden-fixture comparison and for
the S0 harness to measure code-link precision/recall.

#### Scenario: same snapshot yields the same links and evidence

- **WHEN** the linker runs twice on one frozen snapshot
- **THEN** the canonical links and `link-evidence` rows are result-set equal under canonical ordering across both runs
- **AND** `tests/test_code_claim_autolink.py::test_linker_deterministic` passes

### Requirement: REQ-KG-040 — Ambiguous mention is not promoted (Unwanted)

If a mention is ambiguous — multiple symbols match — then the system SHALL store
each candidate as a `link-evidence` row and SHALL NOT promote any of them to a
canonical `code-claim-link` without the second-stage decision (S9).

Rationale: silently promoting one of several matches manufactures a false anchor;
deferring to the learned ranker keeps ambiguous cases honest until S9 decides.

#### Scenario: ambiguous symbol match stays evidence-only

- **WHEN** the linker encounters a mention that resolves to more than one `code-node` symbol
- **THEN** each matching candidate is stored as a `link-evidence` row
- **AND** no candidate becomes a canonical `code-claim-link`
- **AND** `tests/test_code_claim_autolink.py::test_ambiguous_mention_not_promoted` passes
