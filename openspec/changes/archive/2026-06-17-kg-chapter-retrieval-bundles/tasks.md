# Tasks

- [x] Author the chapter-retrieval-bundle graph relation and serialized bundle
      schema. (REQ-CHAP-001, REQ-CHAP-003)
- [x] Add projector tests proving one row per chapter and ledger byte identity.
      (REQ-CHAP-001)
- [x] Add projector tests for ranked communities, load-bearing claims, open
      rebuttals, and source-span anchors. (REQ-CHAP-002)
- [x] Add structured serializer/schema validation tests through the
      book-compose consumer path. (REQ-CHAP-003)
- [x] Add latest-per-id rebuttal tests for open, addressed, and dismissed
      counter-claims. (REQ-CHAP-004)
- [x] Add a frozen golden and two-run canonical equality test. (REQ-CHAP-005)
- [x] Add minimal span cover tests with the fixed claim-id/span-id tie-break.
      (REQ-CHAP-006)
- [x] Add optional code-link inclusion/omission tests. (REQ-CHAP-007)
- [x] Add unanchored load-bearing flag tests. (REQ-CHAP-008)
- [x] Implement `scripts/project_chapter_bundle.py` without ledger writes or
      backend bypasses. (REQ-CHAP-001..008)
- [x] Implement the book-compose serializer and prompt scaffold. (REQ-CHAP-003)
- [x] Run focused CHAP tests plus full book-knowledge and book-compose suites.
      (REQ-CHAP-001..008)
