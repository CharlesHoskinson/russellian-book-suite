# Tasks

- [x] Declare `proof-obligation`, `verification-artifact`, and `requires-proof` in `kg-schema.edn`. (REQ-PROOF-001)
- [x] Add JSON Schemas and validators for the proof-obligation lifecycle and verification artifacts. (REQ-PROOF-001)
- [x] Create an append-only pending obligation for each requires-proof claim without mutating the claim ledger. (REQ-PROOF-002)
- [x] Dispatch checker runs through an injected seam and record discharged artifacts. (REQ-PROOF-003, REQ-PROOF-008)
- [x] Record refutations with committed countermodel paths. (REQ-PROOF-004)
- [x] Project proof obligations, verification artifacts, and requires-proof rows into Cozo. (REQ-PROOF-001, REQ-PROOF-002, REQ-PROOF-003)
- [x] Gate math/science writer assertions on discharged or waived obligation state. (REQ-PROOF-005, REQ-PROOF-006)
- [x] Add deterministic scientific-claim-check flags for missing units and reporting. (REQ-PROOF-007)
- [x] Add `gated-sentence-escape` as a hard book-qa sentinel failure. (REQ-PROOF-009)
- [x] Cover every requirement with exact-name tests in the owning skill. (REQ-PROOF-001, REQ-PROOF-002, REQ-PROOF-003, REQ-PROOF-004, REQ-PROOF-005, REQ-PROOF-006, REQ-PROOF-007, REQ-PROOF-008, REQ-PROOF-009)
