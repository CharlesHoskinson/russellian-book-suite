# Capability: attributed-generation (delta for kg-writer-assertion-contract)

This change ADDS the `attributed-generation` capability. All requirements below are new.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **writer-assertion** — a `writer-assertion` row materialized per generated
  sentence: `sentence-text`, `asserts-claim` (≥1 `claim.id`), `cites-span` (≥1
  `source-span.id`), `citation-check-status`, `revision-origin`.
- **atomic fact** — a `draft-atomic-fact` row: one independently checkable
  proposition decomposed from draft prose (FActScore), mapped to a claim.
- **novel-draft-claim** — an atomic fact with no matching claim in the ledger: a
  candidate claim the draft asserts but the KG does not yet hold.
- **partial-support** — a `citation-check-status` value marking a sentence the
  cited span supports incompletely; such a sentence is published only in a hedged,
  non-canonical form.
- **faithfulness check** — the post-generation sentence→span support check (a small
  NLI / citation-faithfulness model behind a seam, stubbable via an injected
  `llm_call`) returning `full` / `partial` / `none`.

## ADDED Requirements

### Requirement: REQ-ATTR-001 — Sentence binding (Ubiquitous)

The `writer-assertion` SHALL bind each generated sentence to at least one
`claim.id` via `asserts-claim` and at least one `source-span.id` via `cites-span`.

Rationale: the binding is what makes a sentence traceable to the claim and span it
asserts; an unbound sentence is exactly the ephemeral output the brief removes.

#### Scenario: every generated sentence is bound to a claim and a span

- **WHEN** a sentence is generated and recorded as a `writer-assertion`
- **THEN** its `asserts-claim` holds at least one `claim.id` and its `cites-span` holds at least one `source-span.id`
- **AND** a sentence with an empty `asserts-claim` or empty `cites-span` is rejected rather than recorded
- **AND** `tests/test_writer_assertion.py::test_assertion_binds_claim_and_span` passes

### Requirement: REQ-ATTR-002 — Assertion recorded on generation (Event-driven)

When a sentence is generated, the system SHALL record a `writer-assertion`
carrying that sentence's `asserts-claim` and `cites-span`.

Rationale: the assertion is materialized at generation time, so the ledger holds
the binding for every sentence the writer emits, not only those that are checked.

#### Scenario: generating a sentence materializes a writer-assertion

- **WHEN** `book-compose` generates a sentence for a paragraph
- **THEN** exactly one `writer-assertion` row exists for that sentence carrying its `asserts-claim` and `cites-span`
- **AND** `tests/test_writer_assertion.py::test_generation_records_assertion` passes

### Requirement: REQ-ATTR-003 — Citation check status (Event-driven)

When a `writer-assertion` is checked, the sentence→span faithfulness check SHALL
set `citation-check-status` to exactly one of `full`, `partial`, or `none`.

Rationale: a three-valued status (not binary pass/fail) is what lets `partial`
route to a hedge instead of a rewrite, per the brief's `partial-support` state.

#### Scenario: check sets a three-valued status

- **WHEN** the faithfulness check runs on a `writer-assertion` against its cited span
- **THEN** `citation-check-status` is set to one of `full`, `partial`, or `none`
- **AND** a sentence fully entailed by its span resolves to `full` and one contradicted by it resolves to `none`
- **AND** `tests/test_writer_assertion.py::test_citation_check_sets_status` passes

### Requirement: REQ-ATTR-004 — Revise or downgrade on weak support (Unwanted)

If the support check returns `none` or `partial`, then the system SHALL revise the
sentence from the cited span or downgrade it to a hedged non-canonical assertion
flagged `partial-support`, and SHALL NOT publish it unchanged.

Rationale: an unfaithful sentence must never reach the page as-is; revise-from-span
(RARR) or an explicit hedge is the only permitted resolution.

#### Scenario: an unfaithful sentence is revised or hedged, never published as-is

- **WHEN** the faithfulness check returns `none` or `partial` for a sentence
- **THEN** the sentence is either revised from its cited span and re-checked, or downgraded to a hedged non-canonical form flagged `partial-support`
- **AND** the original unchanged sentence is not published
- **AND** `tests/test_writer_assertion.py::test_weak_support_revises_or_downgrades` passes

### Requirement: REQ-ATTR-005 — Revision audit trail (Ubiquitous)

The `revision-origin` field SHALL record how and why a sentence was revised,
yielding an audit trail from the published sentence back to its check result and
revision step.

Rationale: a downgrade or rewrite that leaves no trace is unauditable; the writer
and reviewers must be able to see why a sentence was changed.

#### Scenario: a revised sentence carries its origin

- **WHEN** a sentence is revised or downgraded after a failed check
- **THEN** its `revision-origin` records the triggering `citation-check-status` and the revision action taken
- **AND** an unrevised `full`-support sentence carries an origin marking it unrevised
- **AND** `tests/test_writer_assertion.py::test_revision_origin_audit_trail` passes

### Requirement: REQ-ATTR-006 — Atomic-fact mapping (Event-driven)

When draft prose is decomposed, each `draft-atomic-fact` SHALL map either to an
existing claim or to a `novel-draft-claim`.

Rationale: FActScore decomposition makes every checkable proposition in the draft
accountable to the ledger; a fact is either already a claim or a candidate one.

#### Scenario: decomposition maps each fact to a claim or a novel-draft-claim

- **WHEN** a paragraph of draft prose is decomposed into atomic facts
- **THEN** each atomic fact carries a mapping to an existing `claim.id` or is marked a `novel-draft-claim`
- **AND** no atomic fact is left unmapped
- **AND** `tests/test_writer_assertion.py::test_atomic_fact_maps_to_claim_or_novel` passes

### Requirement: REQ-ATTR-007 — Novel-draft-claim blocks publication (Unwanted)

If an atomic fact maps to a `novel-draft-claim`, then the system SHALL block
publication of that paragraph until the claim is ingested with evidence or the fact
is removed.

Rationale: an unsupported novel assertion is a hallucination risk; the revise loop
runs against the KG, not the open web, and the paragraph waits until the gap is
closed.

#### Scenario: a paragraph with a novel-draft-claim cannot publish

- **WHEN** a paragraph contains an atomic fact mapped to a `novel-draft-claim`
- **THEN** publication of that paragraph is blocked
- **AND** publication unblocks once the `novel-draft-claim` is ingested with evidence or the fact is removed
- **AND** `tests/test_writer_assertion.py::test_novel_draft_claim_blocks_publication` passes

### Requirement: REQ-ATTR-008 — Offline, freezable, deterministic check (Ubiquitous)

The faithfulness check SHALL be offline and freezable — no live web, an
injectable/stubbable `llm_call` — and SHALL be deterministic given a frozen model
and prompt.

Rationale: the check is on the publication path and feeds S0's goldens; it must run
without network and return the same status for the same input so the benchmark can
golden it.

#### Scenario: the check is offline and reproducible

- **WHEN** the faithfulness check runs twice on one `writer-assertion` with a stubbed `llm_call` and a frozen prompt
- **THEN** it makes no network call and returns the same `citation-check-status` both times
- **AND** `tests/test_writer_assertion.py::test_check_offline_and_deterministic` passes
