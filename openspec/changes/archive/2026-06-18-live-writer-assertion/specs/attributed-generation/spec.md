# Capability: attributed-generation (delta for live-writer-assertion)

This change EXTENDS the `attributed-generation` capability. It ADDS
REQ-ATTR-009…014 to the existing capability; the landed S2 change reached
REQ-ATTR-008, and no existing ID is renumbered. All requirements below are new.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios. These scenarios assert behavior on the live
drafting path, not on isolated library calls.

## Definitions

- **live drafting loop** — the `book-compose` loop that emits a chapter's
  sentences from the V1 bundle scaffold; the real build path this delta binds
  the S2 contract onto, as opposed to the S2 unit harness.
- **on the live path** — exercised by the real drafting loop during a book
  build, not by a direct call into the S2 contract module from its own tests.
- **assembled chapter** — the chapter draft after its sentences are joined into
  publishable prose under `chapters/drafts/`; "before assembly" is the point at
  which the revise-or-downgrade policy must already have resolved a sentence.
- **injectable model seam** — the S2-defined faithfulness/decomposer interface:
  injectable, offline, and freezable, so tests stub it and no live model runs on
  the build's test path.

## ADDED Requirements

### Requirement: REQ-ATTR-009 — Live sentence recorded as a writer-assertion (Event-driven)

When the live drafting loop emits a sentence, the system SHALL record a
`writer-assertion` for that sentence bound to its `asserts-claim` and its
`cites-span`.

Rationale: the S2 contract is dormant until a real sentence is bound to it;
recording one assertion per emitted sentence is what puts the live path under
the contract.

#### Scenario: an emitted sentence becomes a bound writer-assertion

- **WHEN** the live drafting loop emits a sentence for a chapter
- **THEN** a `writer-assertion` is recorded for that sentence, carrying its `asserts-claim` and its `cites-span`
- **AND** `skills/book-compose/tests/test_live_writer_assertion.py::test_emitted_sentence_recorded_as_assertion` passes

### Requirement: REQ-ATTR-010 — Faithfulness check sets citation-check-status (Event-driven)

When a live-drafted sentence is recorded, the system SHALL run the sentence→span
faithfulness check and SHALL set that sentence's `citation-check-status` to
`full`, `partial`, or `none`.

Rationale: an assertion bound to a span is only meaningful once the span is
checked; the live path must produce the status the policy then acts on.

#### Scenario: recording a sentence sets its citation-check-status

- **WHEN** a sentence is recorded as a writer-assertion on the live path
- **THEN** the sentence→span faithfulness check runs and sets `citation-check-status` to one of `full`, `partial`, or `none`
- **AND** `skills/book-compose/tests/test_live_writer_assertion.py::test_faithfulness_check_sets_status` passes

### Requirement: REQ-ATTR-011 — Revise-or-downgrade before assembly (Unwanted)

If the faithfulness check returns `partial` or `none` for a live sentence, then
the system SHALL apply the revise-or-downgrade policy before that sentence is
assembled into the chapter, and SHALL NOT publish the original sentence
unchanged.

Rationale: a sentence its span does not support is exactly what the policy
exists to revise or downgrade; assembling it unchanged would publish an
unfaithful citation.

#### Scenario: a partial/none sentence is resolved before assembly

- **WHEN** a live sentence's `citation-check-status` is `partial` or `none`
- **THEN** the revise-or-downgrade policy is applied before the sentence enters the assembled chapter, and the original sentence is never published unchanged
- **AND** a sentence whose status is `full` is assembled as drafted
- **AND** `skills/book-compose/tests/test_live_writer_assertion.py::test_revise_or_downgrade_before_assembly` passes

### Requirement: REQ-ATTR-012 — Atomic-fact decomposition maps each fact (Event-driven)

When a drafted paragraph is decomposed, the system SHALL map each atomic fact to
an existing claim or to a `novel-draft-claim` on the live path.

Rationale: decomposition is what tells the live path which facts are already
grounded and which are new; an unmapped fact is an unaccounted assertion.

#### Scenario: decomposition maps every atomic fact

- **WHEN** a drafted paragraph is decomposed on the live path
- **THEN** each atomic fact is mapped either to an existing claim or to a `novel-draft-claim`
- **AND** no atomic fact is left unmapped
- **AND** `skills/book-compose/tests/test_live_writer_assertion.py::test_atomic_facts_mapped_to_claim_or_novel` passes

### Requirement: REQ-ATTR-013 — Novel-draft-claim blocks publication (Unwanted)

If a drafted paragraph contains a `novel-draft-claim`, then the system SHALL
block publication of that paragraph until the claim is ingested via
`qa/proposed-transitions.jsonl` or the fact is removed.

Rationale: publishing a paragraph that asserts an un-ingested claim would write
prose ahead of the ledger; routing the claim through
`qa/proposed-transitions.jsonl` keeps ingestion owned by book-knowledge.

#### Scenario: a novel-draft-claim paragraph is withheld until resolved

- **WHEN** a drafted paragraph contains a `novel-draft-claim`
- **THEN** publication of that paragraph is blocked until the claim is ingested via `qa/proposed-transitions.jsonl` or the fact is removed
- **AND** a paragraph whose facts all map to existing claims is not blocked
- **AND** `skills/book-compose/tests/test_live_writer_assertion.py::test_novel_draft_claim_blocks_publication` passes

### Requirement: REQ-ATTR-014 — Live touchpoints use the injectable seam (Ubiquitous)

The live faithfulness and decomposer touchpoints SHALL use the injectable,
offline, freezable seam defined by S2, and the build's test path SHALL stub them
so that no live model runs.

Rationale: keeping the faithfulness/decomposer behind the S2 seam keeps the live
build deterministic and offline; the concrete model is a design-time decision,
not a V2 dependency.

#### Scenario: the live path runs the stub seam with no live model

- **WHEN** the live drafting loop runs its faithfulness check and paragraph decomposition under test
- **THEN** both touchpoints resolve through the injectable S2 seam, the seam is stubbed, and no live model is invoked
- **AND** `skills/book-compose/tests/test_live_writer_assertion.py::test_faithfulness_and_decomposer_use_stub_seam` passes
