# Capability: claim-first-drafting (delta for live-warning-surface)

This change ADDS requirements REQ-DRAFT-007..012 to the `claim-first-drafting`
capability. V1 `live-chapter-bundle-input` created the capability through
REQ-DRAFT-006; this delta extends it with the warning surface.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **warning surface** — the section of the writer scaffold that carries caveats
  drawn from the landed S3 grounded-acceptability warnings, S4 contradiction
  alerts, and S5 effective-confidence; the drafting prompt must respect it.
- **contested-load-bearing** — an S3 grounded-acceptability warning that a
  load-bearing claim is not grounded-accepted: it is contested or carries an
  undefended attacker in the argumentation graph.
- **contradiction alert** — an S4 normalized-workbench record that two claims
  stand in an unresolved contradiction; both sides cannot be asserted.
- **effective-confidence threshold** — the configured cutoff below which a
  claim's S5 effective confidence counts as eroded, triggering a hedge with its
  named support-erosion reason.
- **per-prompt budget** — the bounded scaffold size that respects the known
  middle-chapter quality dip; only load-bearing or in-scope warnings are surfaced.

## ADDED Requirements

### Requirement: REQ-DRAFT-007 — Scaffold carries a warning surface (Ubiquitous)

The scaffold SHALL carry a warning surface drawn from the landed S3
grounded-acceptability warnings (contested-load-bearing/undefended-attack,
axiom-only, unsupported-load-bearing), S4 contradiction alerts, and S5
effective-confidence.

Rationale: the three reasoning surfaces are dormant until the writer sees them;
folding them into the scaffold is the whole of move #3 reaching the prose.

#### Scenario: the scaffold exposes the three warning kinds

- **WHEN** the scaffold is built for a chapter whose ledger snapshot carries S3 warnings, an S4 contradiction alert, and S5 effective-confidence
- **THEN** the warning surface presents the S3 grounded-acceptability warnings, the S4 contradiction alerts, and the S5 effective-confidence signal for the in-scope claims
- **AND** `skills/book-compose/tests/test_live_warning_surface.py::test_scaffold_carries_warning_surface` passes

### Requirement: REQ-DRAFT-008 — Contested load-bearing claim instructs defend-or-downgrade (Event-driven)

When a load-bearing claim carries a contested-load-bearing or undefended-attack
warning, the prompt SHALL instruct the writer to defend or downgrade that claim.

Rationale: a load-bearing claim resting on a defeated argument must not be
asserted plainly; the writer either answers the attacker or steps the claim down.

#### Scenario: a contested load-bearing claim draws a defend-or-downgrade instruction

- **WHEN** the scaffold is built for a chapter whose bundle has a load-bearing claim flagged contested-load-bearing or with an undefended attacker
- **THEN** the prompt carries an instruction to defend that claim or downgrade it, naming the claim and its attacker
- **AND** a load-bearing claim with no such S3 warning carries no defend-or-downgrade instruction
- **AND** `skills/book-compose/tests/test_live_warning_surface.py::test_contested_claim_defend_or_downgrade` passes

### Requirement: REQ-DRAFT-009 — Contradiction alert flags both sides (Event-driven)

When a claim appears in a contradiction alert, the scaffold SHALL flag the
conflict so the writer does not assert both sides.

Rationale: asserting both sides of an unresolved contradiction is the exact error
the S4 workbench detects; the surface must carry that alert to the writer.

#### Scenario: a contradiction alert is surfaced against both claims

- **WHEN** the scaffold is built for a chapter whose snapshot lists an unresolved contradiction between two in-scope claims
- **THEN** the warning surface flags the conflict against both claims, instructing the writer not to assert both sides
- **AND** a chapter whose snapshot lists no contradiction alert carries no such flag
- **AND** `skills/book-compose/tests/test_live_warning_surface.py::test_contradiction_alert_flags_both_sides` passes

### Requirement: REQ-DRAFT-010 — Eroded confidence instructs a named hedge (Event-driven)

When a claim's effective-confidence is below the configured threshold, the prompt
SHALL instruct hedged phrasing and SHALL name the support-erosion reason.

Rationale: a claim whose support has eroded must be voiced as conjecture, not
fact, and the reason for the hedge must be legible so the writer can phrase it.

#### Scenario: a below-threshold claim draws a reason-named hedge

- **WHEN** the scaffold is built for a chapter whose snapshot gives an in-scope claim an effective-confidence below the configured threshold
- **THEN** the prompt instructs hedged phrasing for that claim and names its support-erosion reason
- **AND** a claim whose effective-confidence is at or above threshold draws no hedge instruction
- **AND** `skills/book-compose/tests/test_live_warning_surface.py::test_eroded_confidence_named_hedge` passes

### Requirement: REQ-DRAFT-011 — Warning surface is deterministic and consumes landed relations (Ubiquitous)

The warning surface SHALL be deterministic over a ledger snapshot and SHALL
consume the landed S3/S4/S5 relations without running new analysis.

Rationale: V3 adds no analytic power; it reads what S3/S4/S5 already computed, so
the same snapshot yields the same surface and the ledger stays read-only.

#### Scenario: the same snapshot yields the same surface with no recomputation

- **WHEN** the warning surface is built twice over the same ledger snapshot
- **THEN** the two surfaces are byte-identical, the landed S3/S4/S5 relations are read rather than recomputed, and the ledger file is byte-identical before and after
- **AND** `skills/book-compose/tests/test_live_warning_surface.py::test_surface_deterministic_no_new_analysis` passes

### Requirement: REQ-DRAFT-012 — Warning surface respects the per-prompt budget (Ubiquitous)

The warning surface SHALL respect the per-prompt budget, surfacing only
load-bearing or in-scope warnings.

Rationale: folding every warning into one drafting prompt degrades generation (the
middle-chapter dip); only the load-bearing and in-scope caveats earn their place.

#### Scenario: out-of-scope and non-load-bearing warnings are dropped

- **WHEN** the scaffold is built for a chapter whose snapshot carries warnings on out-of-scope and non-load-bearing claims alongside in-scope load-bearing ones
- **THEN** the warning surface carries only the load-bearing or in-scope warnings and omits the rest
- **AND** `skills/book-compose/tests/test_live_warning_surface.py::test_surface_respects_prompt_budget` passes
