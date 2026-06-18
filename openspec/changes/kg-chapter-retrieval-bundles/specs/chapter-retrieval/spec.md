# Capability: chapter-retrieval (delta for kg-chapter-retrieval-bundles)

This change ADDS the `chapter-retrieval` capability. All requirements below are new.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **bundle** — a `chapter-retrieval-bundle` row: the graph-built input handed to
  the writer for one chapter.
- **dominant community** — a `community` whose members account for the largest
  share of the chapter's load-bearing claims, ranked by that share.
- **open rebuttal** — a `counter-claim` targeting an in-scope claim whose
  `cc-status` is `open` (per latest-per-id).
- **minimal span anchor set** — a smallest set of `source-span` rows that covers
  every selected claim at least once, chosen under a fixed tie-break (claim-id then
  span-id lexicographic).

## ADDED Requirements

### Requirement: REQ-CHAP-001 — Bundle projection (Event-driven)

When the `chapter→bundle` projector runs on a chapter id, the system SHALL
materialize exactly one `chapter-retrieval-bundle` row for that chapter and SHALL
leave the ledger unmodified.

Rationale: the bundle is a projection, not a ledger write; it mirrors the
`ledger→cozo` projector's read-only contract (REQ-KG-004).

#### Scenario: projector emits one bundle per chapter

- **WHEN** the projector runs on a chapter with verified supporting claims
- **THEN** exactly one bundle row exists for that chapter id
- **AND** the ledger file is byte-identical before and after
- **AND** `tests/test_chapter_bundle.py::test_one_bundle_per_chapter` passes

### Requirement: REQ-CHAP-002 — Bundle contents (Ubiquitous)

The bundle SHALL carry the chapter's ranked dominant communities, its top
load-bearing claims, the open rebuttals against those claims, and the minimal span
anchor set for those claims.

Rationale: these four are the brief's bundle payload; the writer reasons over them
instead of a flat list.

#### Scenario: bundle holds the four payload sections

- **WHEN** a bundle is materialized for a chapter with communities, load-bearing claims, an open counter-claim, and spans
- **THEN** the bundle exposes ranked communities, load-bearing claims, open rebuttals, and a span anchor set, each non-empty
- **AND** `tests/test_chapter_bundle.py::test_bundle_payload_sections` passes

### Requirement: REQ-CHAP-003 — Structured delivery (Ubiquitous)

The bundle SHALL be delivered to the writer as EDN/JSON conforming to a declared
schema and SHALL NOT be flattened to an unstructured passage list.

#### Scenario: writer receives structured EDN/JSON

- **WHEN** `book-compose` requests the bundle for a chapter
- **THEN** it receives EDN/JSON validating against the bundle schema, with the payload sections addressable by key
- **AND** `tests/test_chapter_bundle.py::test_bundle_is_structured` passes

### Requirement: REQ-CHAP-004 — Open rebuttals surfaced (Event-driven)

When a chapter has a counter-claim with `cc-status` `open` targeting an in-scope
claim, the bundle SHALL surface it in the unresolved-rebuttals section with its
target claim id.

Rationale: an unanswered attack on a load-bearing claim is exactly the caveat the
writer must voice; the bundle is where it must appear.

#### Scenario: open counter-claim appears as an unresolved rebuttal

- **WHEN** the projector runs on a chapter whose load-bearing claim has an open counter-claim
- **THEN** that counter-claim is listed under unresolved rebuttals with its target claim id
- **AND** a counter-claim whose latest status is `addressed` or `dismissed` is excluded
- **AND** `tests/test_chapter_bundle.py::test_open_rebuttal_surfaced` passes

### Requirement: REQ-CHAP-005 — Deterministic projection (Ubiquitous)

The projector SHALL be a deterministic function of a ledger snapshot, producing
result-set-equal bundles for the same snapshot.

#### Scenario: same snapshot yields the same bundle

- **WHEN** the projector runs twice on one frozen snapshot
- **THEN** the two bundles are result-set-equal under canonical ordering
- **AND** `tests/test_chapter_bundle.py::test_projection_deterministic` passes

### Requirement: REQ-CHAP-006 — Minimal span anchors (Ubiquitous)

The bundle's span anchor set SHALL cover every selected claim at least once and
SHALL be minimal under the fixed tie-break (claim-id then span-id lexicographic).

Rationale: the writer needs the smallest faithful anchor set; a fixed tie-break
keeps it golden-able.

#### Scenario: anchors cover all claims and are minimal

- **WHEN** a bundle is built for claims with overlapping spans
- **THEN** every selected claim has at least one anchoring span and no span can be removed while preserving coverage
- **AND** ties resolve by the fixed order
- **AND** `tests/test_chapter_bundle.py::test_minimal_span_cover` passes

### Requirement: REQ-CHAP-007 — Code↔claim links where applicable (Optional)

Where the chapter describes software and `code-claim-link` rows exist for its
claims, the bundle SHALL include those links so the writer can ground software
descriptions in the code graph.

#### Scenario: software chapter carries its code links

- **WHEN** the projector runs on a chapter whose claims have `code-claim-link` rows
- **THEN** the bundle includes those links keyed to their claims
- **AND** a chapter with no code links omits the section rather than emitting an empty-required key
- **AND** `tests/test_chapter_bundle.py::test_code_links_included` passes

### Requirement: REQ-CHAP-008 — Unanchored load-bearing claim is flagged (Unwanted)

If a selected load-bearing claim has no source-span, then the projector SHALL flag
it in the bundle and SHALL NOT emit it as a silently unanchored claim.

Rationale: an unanchored load-bearing claim is a writing hazard; surfacing it lets
the writer downgrade or omit rather than assert without support.

#### Scenario: load-bearing claim without a span is flagged

- **WHEN** the projector encounters a load-bearing claim with no `source-span`
- **THEN** the bundle marks that claim unanchored and lists it under a flags section
- **AND** `tests/test_chapter_bundle.py::test_unanchored_load_bearing_flagged` passes
