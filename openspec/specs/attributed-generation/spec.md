# Capability: attributed-generation

The attributed-generation capability binds every generated sentence to the claim and source-span it asserts, checks sentence→span faithfulness, and revises or downgrades unfaithful sentences. First defined by the `kg-writer-assertion-contract` change (archived).

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
- **live drafting loop** — the book-compose `draft_chapter` loop that emits a
  chapter's sentences from the V1 bundle scaffold; the real build path the S2
  contract is bound onto, as opposed to the S2 unit harness. *(V2)*
- **on the live path** — exercised by the real drafting loop during a build, not by
  a direct call into the contract module from its own tests. *(V2)*
- **assembled chapter** — the chapter draft after its resolved sentences are joined
  into `chapters/drafts/<chapter>/draft.md`; "before assembly" is the point at which
  revise-or-downgrade must already have resolved a sentence. *(V2)*

## Requirements

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
