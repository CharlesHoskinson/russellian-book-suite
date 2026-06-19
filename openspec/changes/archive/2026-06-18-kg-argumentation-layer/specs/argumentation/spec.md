# Capability: argumentation (delta for kg-argumentation-layer)

This change ADDS the `argumentation` capability. All requirements below are new.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **attack** — a `conflicts-with` or `counter-claim` edge from one claim to
  another; the source attacks the target.
- **defense** — a claim defends a target when it attacks each of the target's
  attackers, reinstating the target.
- **undefeated-attacker** — an attacker of a claim that is itself
  grounded-accepted, so its attack stands.
- **grounded extension / acceptance** — Dung's grounded labelling: the least
  fixed point in which a claim is accepted iff every attacker is rejected and
  rejected iff some attacker is accepted; all others are undecided.
- **load-bearing** — a claim carrying a `load-bearing` marker: a claim the chapter
  thesis depends on, for which an unanswered attack is a writing hazard.
- **axiom** — a claim whose status marks it a primitive assumption, admitted
  without further support rather than derived from other claims.

## ADDED Requirements

### Requirement: REQ-ARG-001 — Acceptability rule layer (Ubiquitous)

The rule layer SHALL derive `attacked`, `defended`, `undefeated-attacker`,
`grounded-accepted`, and `grounded-rejected` over the existing
`supports` / `conflicts-with` / `counter-claim` / `sub-argument` / `load-bearing`
edges.

Rationale: the edges are already stored; the move is to read them as a Dung
argumentation framework and derive acceptability, not to add new edges.

#### Scenario: derived relations cover the five labels

- **WHEN** the rule layer runs on a ledger with argument edges
- **THEN** the `attacked`, `defended`, `undefeated-attacker`, `grounded-accepted`, and `grounded-rejected` relations are each populated from those edges
- **AND** no argument edge is written or mutated
- **AND** `tests/test_argumentation.py::test_derived_relations_present` passes

### Requirement: REQ-ARG-002 — One grounded label per claim (Event-driven)

When the argumentation pass runs, the system SHALL assign each in-scope claim
exactly one grounded-acceptance label of `accepted`, `rejected`, or `undecided`.

Rationale: grounded semantics is a total labelling; a claim with two labels or
none would make the warning surface ill-defined.

#### Scenario: every in-scope claim is labelled exactly once

- **WHEN** the argumentation pass runs on a snapshot of in-scope claims
- **THEN** each claim has exactly one of `accepted`, `rejected`, or `undecided`
- **AND** no claim is unlabelled and none carries two labels
- **AND** `tests/test_argumentation.py::test_exactly_one_grounded_label` passes

### Requirement: REQ-ARG-003 — Grounded semantics only (Ubiquitous)

The system SHALL compute grounded semantics only and SHALL NOT compute preferred
or stable extensions.

Rationale: grounded acceptability is deterministic and decidable in plain Datalog;
preferred and stable need an ASP solver and are deferred to S9.

#### Scenario: only the grounded labelling is materialized

- **WHEN** the argumentation pass runs
- **THEN** only the grounded acceptance labels are materialized, with no preferred or stable extension relation
- **AND** `tests/test_argumentation.py::test_grounded_only` passes

### Requirement: REQ-ARG-004 — Contested load-bearing warning (Event-driven)

When a load-bearing claim has an undefeated attacker, the system SHALL emit a
`contested-load-bearing-with-undefended-attack` warning against that claim.

Rationale: a load-bearing claim under a standing, unanswered attack is the central
hazard this layer exists to surface to the writer.

#### Scenario: load-bearing claim with a standing attack warns

- **WHEN** the pass runs on a load-bearing claim whose attacker is grounded-accepted and undefended against
- **THEN** a `contested-load-bearing-with-undefended-attack` warning is emitted naming that claim and the attacker
- **AND** a load-bearing claim whose every attacker is rejected emits no such warning
- **AND** `tests/test_argumentation.py::test_contested_load_bearing_warning` passes

### Requirement: REQ-ARG-005 — Axiom-only support warning (Event-driven)

When a load-bearing claim's only support is an axiom, the system SHALL emit an
`axiom-only-support` warning against that claim.

Rationale: a load-bearing claim resting solely on an admitted assumption is
defensible only by appeal to that axiom; the writer must know to flag it.

#### Scenario: load-bearing claim supported only by an axiom warns

- **WHEN** the pass runs on a load-bearing claim whose supports are all axioms
- **THEN** an `axiom-only-support` warning is emitted naming that claim and the axiom
- **AND** a load-bearing claim with at least one non-axiom support emits no such warning
- **AND** `tests/test_argumentation.py::test_axiom_only_support_warning` passes

### Requirement: REQ-ARG-006 — Minimal justification per warning (Ubiquitous)

Each warning SHALL carry a minimal justification — the defeater set or the missing
support — so the writer can defend or downgrade the claim.

Rationale: a warning without its cause is unactionable; the bounded justification
names exactly what to answer.

#### Scenario: warning names its defeaters or missing support

- **WHEN** a contested-load-bearing or unsupported-load-bearing warning is emitted
- **THEN** it carries the defeater set or the missing-support note that explains why the claim is not grounded-accepted
- **AND** the justification is bounded rather than the full recursive derivation
- **AND** `tests/test_argumentation.py::test_warning_minimal_justification` passes

### Requirement: REQ-ARG-007 — Deterministic acceptance over a snapshot (Ubiquitous)

The acceptance computation SHALL be a deterministic function of a ledger snapshot,
producing result-set-equal labels for the same snapshot, and SHALL compile through
the existing EDN→Cozo path with no new engine.

Rationale: grounded acceptability is the least fixed point and is unique per
snapshot; result-set equality makes it golden-able and keeps it on the existing
seam.

#### Scenario: same snapshot yields the same labels through the existing path

- **WHEN** the argumentation pass runs twice on one frozen snapshot
- **THEN** the two label sets are result-set-equal under canonical ordering
- **AND** the rules compile through the existing EDN→Cozo path with no new engine
- **AND** `tests/test_argumentation.py::test_acceptance_deterministic` passes
