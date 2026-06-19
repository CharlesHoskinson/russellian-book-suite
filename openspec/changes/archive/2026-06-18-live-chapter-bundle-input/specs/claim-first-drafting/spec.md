# Capability: claim-first-drafting (delta for live-chapter-bundle-input)

This change ADDS the `claim-first-drafting` capability. All requirements below are new.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **drafting step** — the `book-compose` step that produces a chapter draft from
  the chapter's evidence; the live path this capability redirects through the bundle.
- **writer scaffold** — the structured input the drafting prompt is built from: for
  this capability, the `chapter-retrieval-bundle`, not a flat claim list.
- **bundle order** — the order the bundle presents its load-bearing claims (ranked,
  per S1 REQ-CHAP-002); the order the drafting prompt preserves.
- **claim-first, citation-first** — presenting each load-bearing claim together with
  its minimal source-span anchor, so the smallest support unit the writer sees is a
  claim plus its anchor.

## ADDED Requirements

### Requirement: REQ-DRAFT-001 — Bundle is the writer scaffold (Ubiquitous)

The drafting step SHALL build its writer scaffold from the chapter's
`chapter-retrieval-bundle` and SHALL NOT fall back to a flat verified-claim list as
the scaffold.

Rationale: claim-first drafting is the whole of move #1 reaching the prose; a flat
list is exactly the passage pile the bundle replaces.

#### Scenario: a drafted chapter is scaffolded from its bundle

- **WHEN** the drafting step runs on a chapter that has a `chapter-retrieval-bundle`
- **THEN** the writer scaffold is built from that bundle (its communities, load-bearing claims, rebuttals, and span anchors), not from a flat claim list
- **AND** `skills/book-compose/tests/test_live_chapter_bundle_input.py::test_scaffold_built_from_bundle` passes

### Requirement: REQ-DRAFT-002 — Prompt built from the bundle scaffold (Event-driven)

When a chapter is drafted, the system SHALL build the drafting prompt from the
bundle's prompt scaffold and payload sections (thesis, ordered support claims with
anchors, rebuttal caveats).

Rationale: the bundle already computes a prompt scaffold (S1); the live path must
use it so the generated prose follows the claim-first structure.

#### Scenario: the drafting prompt follows the bundle scaffold

- **WHEN** the drafting step builds a prompt for a chapter
- **THEN** the prompt contains the bundle's thesis cue, its ordered support claims, and a caveat line for each open rebuttal, derived from the bundle scaffold
- **AND** `skills/book-compose/tests/test_live_chapter_bundle_input.py::test_prompt_follows_bundle_scaffold` passes

### Requirement: REQ-DRAFT-003 — Read-only bundle access through the seam (Ubiquitous)

The drafting step SHALL obtain the bundle via the book-knowledge projector through
`sibling_skills`, SHALL leave the ledger byte-identical, and SHALL write only under
`chapters/`.

Rationale: ledger ownership stays with book-knowledge; the drafting step is a
read-only consumer that writes only its own chapter output.

#### Scenario: drafting reads the bundle and writes only chapters

- **WHEN** the drafting step obtains a bundle and produces a draft
- **THEN** the bundle is loaded through `sibling_skills` from book-knowledge, the ledger file is byte-identical before and after, and only `chapters/` paths are written
- **AND** `skills/book-compose/tests/test_live_chapter_bundle_input.py::test_bundle_access_read_only` passes

### Requirement: REQ-DRAFT-004 — Claim-first, citation-first presentation (Ubiquitous)

The scaffold SHALL present the bundle's load-bearing claims in bundle order, each
paired with its minimal source-span anchor, so the smallest support unit presented
is a claim plus an anchor.

Rationale: citation-first presentation is what makes the downstream writer-assertion
contract (V2) bindable; a claim shown without its anchor cannot be cited.

#### Scenario: each load-bearing claim is shown with its anchor in order

- **WHEN** the scaffold is built from a bundle with ordered load-bearing claims and span anchors
- **THEN** each load-bearing claim appears in bundle order paired with its minimal span anchor
- **AND** a claim with no anchor is not presented as a citeable support claim
- **AND** `skills/book-compose/tests/test_live_chapter_bundle_input.py::test_claims_presented_with_anchors_in_order` passes

### Requirement: REQ-DRAFT-005 — Open rebuttals caveated (Event-driven)

When the bundle surfaces an open rebuttal against an in-scope claim, the drafting
prompt SHALL include a caveat for that rebuttal.

Rationale: an unanswered attack on a load-bearing claim is exactly the caveat the
writer must voice; the bundle surfaces it and the prompt must carry it.

#### Scenario: an open rebuttal becomes a prompt caveat

- **WHEN** the drafting step builds a prompt for a chapter whose bundle lists an open rebuttal
- **THEN** the prompt includes a caveat naming that rebuttal and its target claim
- **AND** a chapter whose bundle lists no open rebuttal carries no such caveat
- **AND** `skills/book-compose/tests/test_live_chapter_bundle_input.py::test_open_rebuttal_caveated` passes

### Requirement: REQ-DRAFT-006 — Unanchored load-bearing claim not assertable (Unwanted)

If the bundle flags an unanchored load-bearing claim, then the drafting step SHALL
NOT present that claim as an assertable support and SHALL surface the flag instead.

Rationale: an unanchored load-bearing claim is a writing hazard the bundle already
flags (S1 REQ-CHAP-008); the live path must honor the flag rather than draft an
unsupported assertion.

#### Scenario: a flagged unanchored claim is withheld from assertion

- **WHEN** the drafting step processes a bundle that flags a load-bearing claim as unanchored
- **THEN** that claim is not presented as an assertable support, and its unanchored flag is surfaced in the scaffold
- **AND** `skills/book-compose/tests/test_live_chapter_bundle_input.py::test_unanchored_claim_not_assertable` passes
