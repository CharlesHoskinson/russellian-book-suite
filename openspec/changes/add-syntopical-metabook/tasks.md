# Tasks

## 0. Repo verification and change-folder scaffolding
- [x] 0.1 Verify repo state and create feature branch
- [x] 0.2 Verify existing OpenSpec installation
- [x] 0.3 Create change folder skeleton
- [x] 0.4 Author proposal.md
- [x] 0.5 Mirror the design doc
- [x] 0.6 Transcribe EARS into delta specs
- [x] 0.7 Mirror this plan as tasks.md
- [x] 0.8 Push the branch

## 1. Foundation + ABI
- [x] 1.1 Scaffold sibling_skills package
- [x] 1.2 Implement load_skill_api with TDD
- [x] 1.3 Set up import-linter to enforce no-direct-http (NFR-4)
- [x] 1.4 Set up no-shadow-writes pytest plugin (NFR-5)
- [x] 1.5 Scaffold empty skill_api.py placeholders on existing skills
- [x] 1.6 Deploy new skills to runtime location

## 2. scrapling-fetch core
- [x] 2.1 Skill scaffolding
- [x] 2.2 Typed exceptions
- [x] 2.3 Session construction
- [x] 2.4 fetch() + Page dataclass
- [x] 2.5 download_pdf() with streaming + sha256 + content-type guard
- [x] 2.6 skill_api.py wiring

## 3. scrapling-fetch adapters
- [x] 3.1 arxiv adapter (REQ-SF-6)
- [x] 3.2 openalex adapter (REQ-SF-7)
- [x] 3.3 semantic_scholar adapter (REQ-SF-8)
- [x] 3.4 doi resolver (REQ-SF-9)
- [x] 3.5 Export adapters from skill_api.py
- [x] 3.6 Live tests behind pytest -m live

## 4. Existing-skill skill_api.py shims
- [x] 4.1 book-knowledge skill_api (IF-BK-1..4)
- [x] 4.2 book-thesis skill_api (IF-BT-1)
- [x] 4.3 russellian-style skill_api (IF-RS-1)
- [x] 4.4 book-compose skill_api (IF-BC-1 consumer side, full impl in Phase 9)

## 5. Booklogic adapter + dev stub + conformance suite
- [x] 5.1 Scaffold syntopical-metabook skill
- [x] 5.2 Dev stub booklogic_stub.py
- [x] 5.3 Python adapter booklogic_adapter.py
- [x] 5.4 JSON-projection bijectivity smoke test (IF-BL-15)

## 6. Metabook Acquire + Veto
- [x] 6.1 expand_seeds (REQ-ACQ-1)
- [x] 6.2 rank_candidates (REQ-ACQ-2)
- [x] 6.3 triage partition (REQ-ACQ-3)
- [x] 6.4 Veto (REQ-VETO-1/2)
- [x] 6.5 download_and_ingest (REQ-ACQ-4/5)
- [x] 6.6 Manifest, HALT, --feed-acquire (REQ-ACQ-6..9)
- [x] 6.7 Acquire integration test against fixtures

## 7. Metabook Synthesize
- [x] 7.1 Topic map (REQ-SYN-1)
- [x] 7.2 Disputed questions via booklogic (REQ-SYN-2)
- [x] 7.3 Concept reconciliation via booklogic (REQ-SYN-3)
- [x] 7.4 Idempotence (REQ-SYN-4)
- [x] 7.5 Citation linter (REQ-SYN-5)
- [x] 7.6 Legacy mode fallback (REQ-SYN-6)

## 8. Metabook Lens + Gap
- [x] 8.1 project_lens (REQ-LENS-1/2/3)
- [x] 8.2 coverage_report (REQ-GAP-1)
- [x] 8.3 --feed-acquire feedback loop (REQ-GAP-2)

## 9. book-compose integration + release validation
- [x] 9.1 book-compose lens consumption (IF-BC-1)
- [x] 9.2 End-to-end smoke
- [x] 9.3 NFR validation pass
- [x] 9.4 Provenance footers (NFR-8)
- [x] 9.5 Update OpenSpec tasks.md and mark draft PR ready
