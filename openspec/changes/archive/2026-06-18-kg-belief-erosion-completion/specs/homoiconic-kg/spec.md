# Capability: homoiconic-kg (delta for kg-belief-erosion-completion)

This change ADDS requirements REQ-KG-028 through REQ-KG-034 to the existing
`homoiconic-kg` capability. It extends the landed capability; it does not restate
or renumber its REQ-KG-001..018 (the prior change ported the claim stack to the
Cozo seam, and a parallel S4 change appends its own REQ-KG block in sprint order).

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **effective-confidence** — a materialized Cozo relation holding, per claim, the
  confidence after erosion: derived from `p-prior`, `p-posterior`, `supports`,
  `derived-from`, `conflicts-with`, `source.trust-score`, and source freshness. The
  `propagate_belief` engine computes the posterior; this relation makes the eroded
  result queryable rather than only appended to the ledger.
- **support-erosion-reason** — the minimal justification set explaining why a
  claim's effective-confidence fell below its prior: the counter-claims and
  parent-weakening derivations responsible for the drop.
- **minimal justification set** — a smallest set of facts (counter-claims,
  weakened parents) whose removal would restore the claim's confidence; the
  erosion analogue of an unsat-core, chosen under a fixed tie-break.
- **why-provenance** — a bounded witness explanation for a claim's
  effective-confidence: the minimal-cardinality derivation supports that account
  for the value, computed on demand and cached in the ledger. Distinct from the
  neurosym-forge provenance sidecar, which is over induced rules, not claim
  derivations.
- **freshness decay** — a time-dependent discount applied to `source.trust-score`
  so a stale high-trust source contributes less by age; an input to the
  effective-confidence derivation.

## ADDED Requirements

### Requirement: REQ-KG-028 — Effective-confidence materialized (Ubiquitous)

The system SHALL materialize `effective-confidence` as a Cozo relation derived
from `p-prior`, `p-posterior`, `supports`, `derived-from`, `conflicts-with`,
`source.trust-score`, and source freshness, holding one row per latest-per-id
claim, and SHALL leave the ledger unmodified.

Rationale: the erosion pass currently appends posteriors back to the ledger only;
materializing the eroded result as a queryable relation is what lets the writer and
S0 read the signal, mirroring the `ledger→cozo` projector's read-only contract
(REQ-KG-004).

#### Scenario: erosion result lands as a queryable relation

- **WHEN** the effective-confidence projector runs on a workspace whose claims have priors, posteriors, supports, conflicts, and source trust
- **THEN** Cozo holds one `effective-confidence` row per latest-per-id claim, each derived from those inputs and source freshness
- **AND** the ledger file is byte-identical before and after
- **AND** `tests/test_belief_erosion.py::test_effective_confidence_materialized` passes

### Requirement: REQ-KG-029 — Erosion reason from minimal justification (Event-driven)

When propagation runs, each claim whose effective-confidence falls below its prior
SHALL carry a `support-erosion-reason` drawn from a minimal justification set
naming the counter-claims or parent-weakening derivations responsible for the drop.

Rationale: a bare lowered number is unusable to the writer; the minimal
justification set tells it *why* the claim eroded so it can caveat or omit.

#### Scenario: eroded claim names its minimal justification

- **WHEN** propagation runs on a claim damped by a counter-claim and a weakened parent
- **THEN** the claim's effective-confidence row carries a `support-erosion-reason` whose justification set is minimal and names that counter-claim and that parent
- **AND** a claim whose confidence did not drop carries no erosion reason
- **AND** `tests/test_belief_erosion.py::test_erosion_reason_minimal` passes

### Requirement: REQ-KG-030 — Refreshed conflicting source erodes the claim (Event-driven)

When a source is refreshed and now conflicts with a claim, that claim's
effective-confidence SHALL drop and its `support-erosion-reason` SHALL name the
refreshed source and the trusted conflict it introduced.

Rationale: a source refresh that turns supporting into conflicting evidence is the
canonical erosion event; the reason must trace the drop to the refreshed source so
the staleness is auditable.

#### Scenario: refresh that introduces a trusted conflict drops confidence

- **WHEN** a high-trust source is refreshed and the refreshed content now conflicts with a claim it formerly supported
- **THEN** the claim's effective-confidence drops and its erosion reason names the refreshed source and the trusted conflict
- **AND** `tests/test_belief_erosion.py::test_refreshed_source_conflict_erodes` passes

### Requirement: REQ-KG-031 — Bounded why-provenance on demand only (Optional)

Where a load-bearing claim is flagged for explanation by the writer or checker, the
system SHALL compute a bounded why-provenance returning minimal-cardinality witness
sets, and SHALL NOT compute why-provenance for every claim.

Rationale: why-provenance for recursive Datalog can be intractable; throttling it to
flagged load-bearing claims keeps the cost bounded while still explaining the claims
that carry the chapter.

#### Scenario: provenance is computed only for flagged load-bearing claims

- **WHEN** a load-bearing claim is flagged for explanation and a non-flagged claim is not
- **THEN** the system returns a bounded minimal-cardinality witness set for the flagged claim and computes no why-provenance for the non-flagged claim
- **AND** the flagged claim's witness set is cached in the ledger
- **AND** `tests/test_belief_erosion.py::test_why_provenance_on_demand` passes

### Requirement: REQ-KG-032 — Source freshness decay (Ubiquitous)

Source trust SHALL carry a freshness decay such that a stale high-trust source is
discounted by age, and the decayed trust SHALL feed the effective-confidence
derivation.

Rationale: a high-trust source that has not been refreshed should not anchor a claim
forever; age-discounting the trust is what lets a fresh conflicting source overtake
a stale supporting one.

#### Scenario: a stale high-trust source is discounted

- **WHEN** effective-confidence is derived for a claim resting on a high-trust source last refreshed long ago and an equal claim resting on a freshly refreshed source
- **THEN** the stale-source claim's contributing trust is discounted by age relative to the fresh-source claim
- **AND** `tests/test_belief_erosion.py::test_freshness_decay` passes

### Requirement: REQ-KG-033 — Deterministic and engine-reusing (Ubiquitous)

Effective-confidence SHALL be deterministic over a ledger snapshot — producing
result-set-equal output for the same snapshot — and SHALL reuse the existing
`propagate_belief` engine without rewriting its erosion mathematics.

Rationale: determinism is required for S0 to golden the relation; reuse is the
sprint's premise — `propagate_belief.py` already implements the Bayesian pass, so
S5 materializes its result rather than reimplementing it.

#### Scenario: same snapshot yields the same relation through the existing engine

- **WHEN** the effective-confidence projector runs twice on one frozen snapshot
- **THEN** the two `effective-confidence` relations are result-set-equal under canonical ordering, and the erosion values are those produced by `propagate_belief` (not a reimplementation)
- **AND** `tests/test_belief_erosion.py::test_effective_confidence_deterministic_reuses_engine` passes

### Requirement: REQ-KG-034 — Why-provenance truncates at the bound (Unwanted)

If a load-bearing claim's why-provenance exceeds the bounded witness cardinality,
then the system SHALL return the bounded witness set marked truncated rather than
computing it unbounded.

Rationale: the bound is the throttle that keeps recursive-Datalog provenance
tractable; exceeding it must degrade to a marked-truncated answer, never to an
unbounded computation.

#### Scenario: oversized provenance returns a marked-truncated witness set

- **WHEN** a flagged load-bearing claim's why-provenance would exceed the bounded cardinality
- **THEN** the system returns the bounded witness set marked truncated and does not compute the full unbounded set
- **AND** `tests/test_belief_erosion.py::test_why_provenance_truncates_at_bound` passes
