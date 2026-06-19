# Capability: claim-first-drafting (delta for live-code-grounding)

This change ADDS REQ-DRAFT-013..018 to the `claim-first-drafting` capability. The
capability already exists (V1 added REQ-DRAFT-001..006; V3 added REQ-DRAFT-007..012);
this delta extends it with the code-grounding section of the scaffold.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **code grounding** — the scaffold section that pairs a claim with the code symbol
  or module it is bound to, so the writer describes software against the real code
  graph rather than from recall.
- **canonical link surfaced** — a `code-claim-link` that S6 derived deterministically
  and unambiguously (file path + exact symbol); only these are shown in the scaffold.
- **software chapter** — a chapter whose claims carry at least one canonical
  `code-claim-link`; a chapter with none is a non-software chapter for this capability.
- **evidence-only invisibility** — an ambiguous link candidate that S6 retained as
  evidence-only is never surfaced to the writer, so the scaffold offers no false
  anchor.

## ADDED Requirements

### Requirement: REQ-DRAFT-013 — Code grounding for software chapters (Optional)

Where a chapter describes software, the scaffold SHALL surface the canonical
`code-claim-link` rows for its claims so the writer grounds software descriptions in
the code graph.

Rationale: a software description drafted without a view of the code graph is exactly
the invented-API risk the deterministic linker was built to remove.

#### Scenario: a software chapter scaffold carries code grounding

- **WHEN** the scaffold is built for a chapter whose claims carry canonical `code-claim-link` rows
- **THEN** the scaffold surfaces a code-grounding section pairing those claims with their linked code symbols or modules
- **AND** `skills/book-compose/tests/test_live_code_grounding.py::test_software_chapter_surfaces_code_grounding` passes

### Requirement: REQ-DRAFT-014 — Only canonical links surfaced (Ubiquitous)

The scaffold SHALL surface only canonical (deterministic, unambiguous)
`code-claim-link` rows to the writer and SHALL NOT surface ambiguous evidence-only
candidates.

Rationale: an ambiguous candidate shown as an anchor is a false anchor; the writer
must ground only on links S6 resolved unambiguously.

#### Scenario: ambiguous candidates are excluded from the scaffold

- **WHEN** a claim carries both a canonical link and ambiguous evidence-only candidates
- **THEN** the scaffold surfaces the canonical link and surfaces none of the evidence-only candidates
- **AND** `skills/book-compose/tests/test_live_code_grounding.py::test_only_canonical_links_surfaced` passes

### Requirement: REQ-DRAFT-015 — Load-bearing claim paired with its symbol (Event-driven)

When a load-bearing claim has a canonical `code-claim-link`, the scaffold SHALL pair
that claim with its linked code symbol or module.

Rationale: the load-bearing claims are the ones whose software descriptions carry the
chapter; pairing each with its real symbol is what grounds the prose.

#### Scenario: a linked load-bearing claim shows its code symbol

- **WHEN** the scaffold is built for a chapter with a load-bearing claim that has a canonical `code-claim-link`
- **THEN** that claim appears in the code-grounding section paired with its linked code symbol or module
- **AND** `skills/book-compose/tests/test_live_code_grounding.py::test_load_bearing_claim_paired_with_symbol` passes

### Requirement: REQ-DRAFT-016 — Read-only, deterministic grounding (Ubiquitous)

The code grounding SHALL be read-only over the code graph and the ledger, and SHALL
be deterministic over a snapshot.

Rationale: grounding is a consumer of the landed S6 relation; it derives no new links
and must not mutate the graph or the ledger, and the same snapshot must yield the
same grounding.

#### Scenario: grounding mutates nothing and repeats identically

- **WHEN** the scaffold's code grounding is built twice over the same snapshot of the code graph and ledger
- **THEN** the code graph and ledger files are byte-identical before and after, and both runs produce identical grounding
- **AND** `skills/book-compose/tests/test_live_code_grounding.py::test_grounding_read_only_deterministic` passes

### Requirement: REQ-DRAFT-017 — Evidence-only claim gets no grounding (Unwanted)

If a claim has only evidence-only (ambiguous) links, then the scaffold SHALL surface
no code grounding for that claim.

Rationale: an evidence-only candidate is not a resolved anchor; grounding the writer
on it would invite the invented-API error the canonical-only rule exists to prevent.

#### Scenario: a claim with only ambiguous links is left ungrounded

- **WHEN** the scaffold is built for a claim whose only `code-claim-link` rows are evidence-only
- **THEN** that claim appears with no code grounding and no code symbol anchor
- **AND** `skills/book-compose/tests/test_live_code_grounding.py::test_evidence_only_claim_not_grounded` passes

### Requirement: REQ-DRAFT-018 — Non-software chapter omits the section (Ubiquitous)

A non-software chapter with no code links SHALL omit the code-grounding section and
SHALL NOT emit an empty required block.

Rationale: an empty required block is scaffold noise the writer must read past; a
chapter with no code links has nothing to ground and the section is simply absent.

#### Scenario: a chapter with no code links has no grounding section

- **WHEN** the scaffold is built for a chapter whose claims carry no canonical `code-claim-link` rows
- **THEN** the scaffold contains no code-grounding section rather than an empty one
- **AND** `skills/book-compose/tests/test_live_code_grounding.py::test_non_software_chapter_omits_section` passes
