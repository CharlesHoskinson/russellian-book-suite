# Change: booklogic-cleanup

**Sprint:** 1 of 5 (BookLogic v0.4 finish)
**Branch:** `feat/booklogic-cleanup`
**GitHub Milestone:** `booklogic-cleanup`

## Why

Three sources of drift threaten the v0.4 mission's coherence:

1. The Codex two-agent collaboration scaffolding (`docs/codex-wiki/`, two
   `2026-05-15-codex-*.md` handoff briefs, `docs/specs/2026-05-15-codex-handoff-design.md`,
   `openspec/changes/codex-phase-0/`) is dead weight now that work is Claude-only.
2. `verifiers/bermuda/rules/seed.edn` and `verifiers/bermuda/rules/grounded.edn`
   are still JSON-stamped-as-EDN — the D1 boundary fix from PR-1 missed them.
3. The six `verifiers/bermuda/cljs-orchestrator/` modules (`bridge`, `core`,
   `ir`, `nl_to_fol`, `phases`, `unify`) have zero tests and zero CI coverage.
   `nl_to_fol/claim->formula` has a latent schema collision the audit
   flagged.

## What

- Delete the Codex scaffolding (4 dirs/file-sets).
- Convert `seed.edn` + `grounded.edn` to real EDN.
- Add `cljs.test` coverage for the six in-tree Bermuda CLJS modules via a new
  `shadow-cljs :test` target.
- Fix the `nl_to_fol/claim->formula` bug.
- Add a `cljs-bermuda-test` CI job.

## Capabilities touched

- `edn-boundary` — ADD requirements for data-file hygiene (seed.edn, grounded.edn round-trip real EDN)
- `bermuda-rules` — ADD requirements for the two file shapes
- `cljs-orchestrator` — ADD requirements for module test coverage; ADD requirement for the `claim->formula` fix

## Implementation notes

See `docs/plans/2026-05-17-booklogic-cleanup.md` for the full TDD plan
(6 phases, 20 tasks). `tasks.md` in this directory is the executor's
checklist; the TDD plan is the exhaustive command/code reference.

## Acceptance

- `grep -ri "codex" docs/` returns nothing in active documentation
- `verifiers/bermuda/rules/seed.edn` and `verifiers/bermuda/rules/grounded.edn`
  round-trip through `read_edn_file` with `Keyword` keys
- `cljs-bermuda-test` CI job is green
- `nl_to_fol/claim->formula` passes the failing-then-fixing test
- All REQ IDs added by this change are satisfied by tests citing them
