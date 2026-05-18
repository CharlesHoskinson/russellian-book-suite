# Tasks: tier1-fact-extraction-preview

See `docs/plans/2026-05-18-tier1-general-purpose.md` Phase A for full
TDD steps. Task numbers correspond 1:1.

## Phase A.1 — `extract_preview.py` core

- [ ] A1.1: `verifiers/osmotic_pressure/scripts/tests/test_extract_preview.py` (write failing test). (REQ-INGEST-040)
- [ ] A1.2: `verifiers/osmotic_pressure/scripts/extract_preview.py` minimal implementation. (REQ-INGEST-040)
- [ ] A1.3: Re-run pytest — 1 passed.
- [ ] A1.4: Add `--threshold` CLI flag + OPAQUE-fraction gate. (REQ-INGEST-041)
- [ ] A1.5: Add `--dry-run` flag. (REQ-INGEST-042)
- [ ] A1.6: Add JSON tail output. (REQ-INGEST-043)
- [ ] A1.7: Commit.

## Phase A.2 — Per-verifier Makefile wiring

- [ ] A2.1: Add `extract` target to `verifiers/osmotic_pressure/Makefile`. (REQ-INGEST-044)
- [ ] A2.2: Wire `extract` into the `ci` target between `build` and `smoke`. (REQ-INGEST-045)
- [ ] A2.3: Add `extract` target to `verifiers/bermuda/Makefile`. (REQ-INGEST-044)
- [ ] A2.4: Wire `extract` into bermuda's `ci` target. (REQ-INGEST-045)
- [ ] A2.5: Commit.

## Phase A.3 — Scaffold template

- [ ] A3.1: Add `extract` target to `skills/neurosym-forge/assets/project-template/Makefile.tmpl`. (REQ-INGEST-046)
- [ ] A3.2: Add `scripts/extract_preview.py.tmpl` (shim that imports from a vendored lib, mirroring the codegen_axioms.py pattern). (REQ-INGEST-047)
- [ ] A3.3: Add a regression test in `skills/neurosym-forge/tests/regression/test_sprint5_bug_catches.py` that re-injects a JS-style `(?<v>)` regex into a baked project's lifts.edn and asserts `make ci` fails at the extract gate. (REQ-INGEST-048)
- [ ] A3.4: Commit.

## Phase A.4 — Open PR

- [ ] A4.1: Push branch `feat/tier1-fact-extraction-preview` and open PR.
- [ ] A4.2: Merge on green CI.
