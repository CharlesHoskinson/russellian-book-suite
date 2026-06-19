## Tasks

- [x] Trace the current `book-compose` draft/build flow and identify the executable draft seam. (REQ-DRAFT-001, REQ-DRAFT-003)
- [x] Add a live `draft_chapter` step that obtains `chapter_bundle.build_chapter_bundle_input` through the existing serializer. (REQ-DRAFT-001, REQ-DRAFT-003)
- [x] Build a deterministic bundle scaffold from the S1 payload and prompt scaffold. (REQ-DRAFT-002)
- [x] Render ordered load-bearing claims with minimal source-span anchors and withhold unanchored claims from assertable support. (REQ-DRAFT-004, REQ-DRAFT-006)
- [x] Render open rebuttals as prompt caveats. (REQ-DRAFT-005)
- [x] Write draft artifacts only under `chapters/drafts/<chapter_id>/` and keep ledger access read-only. (REQ-DRAFT-003)
- [x] Add `test_live_chapter_bundle_input.py` covering REQ-DRAFT-001 through REQ-DRAFT-006 on the live draft path. (REQ-DRAFT-001..006)
