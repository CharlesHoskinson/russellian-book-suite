# Capability: proof-obligations (delta for live-proof-gate)

This change ADDS REQ-PROOF-010..015 to the existing `proof-obligations` capability.
The landed S7 change reached REQ-PROOF-009 (the obligation entity, lifecycle,
gate, and render policy); these requirements extend that sequence with the live
producer and end-to-end gating. No existing IDs are renumbered.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **gated-sentences producer** — the live pass that emits `qa/gated-sentences.jsonl`,
  one row per rendered sentence, recording the claim it asserts, that claim's
  obligation status, and the assertion kind; the producer the S7 gate has lacked.
- **live math/science pass** — the `halmos` / `book-compose` writer pass that renders
  math and science chapter sentences from claims; the live path this capability wires
  the S7 render policy and gate through.
- **end-to-end gate** — the S7 book-qa `gated-sentence-escape` gate reading the live
  producer's `qa/gated-sentences.jsonl` on a real build, hard-failing a build whose
  final prose asserts an undischarged-unwaived gated claim.
- **assertion kind** — how a rendered sentence presents its claim: `verified`,
  `conjectural`, or `omitted`; the render mode the S7 policy assigns from the claim's
  obligation status.

## ADDED Requirements

### Requirement: REQ-PROOF-010 — Live pass emits gated-sentences (Event-driven)

When the live math/science writer pass renders a sentence asserting a claim, the
system SHALL emit a `qa/gated-sentences.jsonl` row recording that claim, the claim's
obligation status, and the assertion kind.

Rationale: the S7 gate reads `qa/gated-sentences.jsonl` but nothing emits it on a
real build; the live pass is the missing producer that closes the gap.

#### Scenario: a rendered gated sentence emits a row

- **WHEN** the live math/science pass renders a sentence that asserts a claim carrying a proof obligation
- **THEN** a `qa/gated-sentences.jsonl` row is appended recording the claim id, the claim's obligation status, and the assertion kind
- **AND** `skills/halmos/tests/test_live_proof_gate.py::test_rendered_sentence_emits_gated_row` passes

### Requirement: REQ-PROOF-011 — Emitted rows are the gate's producer (Ubiquitous)

The emitted `qa/gated-sentences.jsonl` rows SHALL be the producer the S7 book-qa
`gated-sentence-escape` gate reads on a real build.

Rationale: the gate was landed in S7 with no live producer; wiring the live pass's
emitted rows into the gate is what makes it fire on an actual chapter.

#### Scenario: the S7 gate consumes the live producer's rows

- **WHEN** a real build emits `qa/gated-sentences.jsonl` from the live pass and the book-qa gate runs
- **THEN** the gate reads those emitted rows and evaluates each gated sentence against its claim's obligation status
- **AND** `skills/book-qa/tests/test_live_proof_gate.py::test_gate_reads_live_gated_sentences` passes

### Requirement: REQ-PROOF-012 — Undischarged claims not rendered verified (State-driven)

While a claim's obligation is undischarged, the live math/science pass SHALL render
the claim omitted or conjectural and SHALL NOT render it as verified.

Rationale: the S7 render policy forbids asserting an undischarged obligation as
verified; the live path must apply that policy when it renders the claim.

#### Scenario: an undischarged claim is rendered conjectural, not verified

- **WHEN** the live pass renders a sentence for a claim whose obligation is undischarged
- **THEN** the sentence's assertion kind is `omitted` or `conjectural` and never `verified`
- **AND** `skills/halmos/tests/test_live_proof_gate.py::test_undischarged_claim_not_verified` passes

### Requirement: REQ-PROOF-013 — Escaped gated claim hard-fails the build (Unwanted)

If a build's final prose asserts an undischarged, unwaived gated claim, then the
QA gate SHALL hard-fail that build end-to-end.

Rationale: an undischarged-unwaived verified assertion reaching the prose is the
exact escape the S7 gate exists to stop; on the live path it must fail the build.

#### Scenario: an undischarged-unwaived assertion fails the gate end-to-end

- **WHEN** a real build's final prose asserts a claim whose obligation is undischarged and unwaived
- **THEN** the book-qa gate hard-fails the build and the build does not pass QA
- **AND** `skills/book-qa/tests/test_live_proof_gate.py::test_escaped_gated_claim_hard_fails` passes

### Requirement: REQ-PROOF-014 — Ownership and no live verifier (Ubiquitous)

The live math/science pass SHALL write only `qa/` and `chapters/`; the gate SHALL
stay owned by book-qa and the obligations by book-knowledge; and no live external
verifier SHALL run on the build's test path.

Rationale: V4 wires the producer and consumer without crossing skill boundaries;
the checker seam stays stubbed so the build's test path runs no external verifier.

#### Scenario: the live pass keeps ownership and runs no verifier

- **WHEN** the live pass runs on a real build and emits its gated sentences
- **THEN** only `qa/` and `chapters/` paths are written, the obligations under book-knowledge are byte-identical, and no external verifier process is invoked on the test path
- **AND** `skills/book-qa/tests/test_live_proof_gate.py::test_ownership_and_no_live_verifier` passes

### Requirement: REQ-PROOF-015 — Waived obligation rendered conjecturally (Optional)

Where a claim's obligation is waived, the live pass SHALL render the claim
conjecturally with the waiver noted.

Rationale: a waiver permits a conjectural mention rather than a verified assertion;
the S7 policy records the waiver, and the live path must carry it into the render.

#### Scenario: a waived obligation renders conjecturally with the waiver noted

- **WHEN** the live pass renders a sentence for a claim whose obligation is waived
- **THEN** the sentence is rendered with assertion kind `conjectural` and its emitted row notes the waiver
- **AND** `skills/halmos/tests/test_live_proof_gate.py::test_waived_obligation_conjectural` passes
