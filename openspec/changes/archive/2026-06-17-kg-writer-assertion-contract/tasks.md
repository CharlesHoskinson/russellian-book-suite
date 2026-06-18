# Tasks

- [x] Decide and document writer-assertion / draft-atomic-fact storage and
      ownership. (REQ-ATTR-001, REQ-ATTR-006, REQ-ATTR-007)
- [x] Add binding validation tests for non-empty `asserts_claim` and
      `cites_span`. (REQ-ATTR-001)
- [x] Add generation-time assertion recording tests. (REQ-ATTR-002)
- [x] Add three-valued citation-check tests using injected `llm_call` fakes.
      (REQ-ATTR-003, REQ-ATTR-008)
- [x] Add revise-or-downgrade tests proving weak support never publishes the
      original unchanged sentence. (REQ-ATTR-004)
- [x] Add revision-origin audit trail tests for unrevised, revised, and
      downgraded paths. (REQ-ATTR-005)
- [x] Add atomic-fact decomposition tests proving each fact maps to a claim or
      novel draft claim. (REQ-ATTR-006)
- [x] Add publication-block tests proving novel draft claims block and route
      proposals to `qa/proposed-transitions.jsonl`. (REQ-ATTR-007)
- [x] Implement book-compose writer assertion and atomic fact modules without
      writes outside `chapters/`. (REQ-ATTR-001..008)
- [x] Implement book-qa proposal writer and update book-knowledge writeback to
      consume `qa/proposed-transitions.jsonl`. (REQ-ATTR-007)
- [x] Run focused ATTR tests plus full affected skill suites. (REQ-ATTR-001..008)
