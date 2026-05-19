# Tasks: tier5-hybrid-query

See `docs/plans/2026-05-19-tier5-metta-runtime.md` Phase R for full TDD
steps. Task numbers correspond 1:1.

## Phase R.1 — Grounded atom skeleton

- [ ] R1.1: Register `(hybrid-match $space $template $hint $k)` as a grounded atom in the Phase O runtime; minimal pass-through implementation that calls `(match ...)` only. (REQ-QUERY-040)
- [ ] R1.2: Register `(neighbors-only $space $hint $k)` as a grounded atom; thin wrapper over Phase Q's `(neighbors ...)`. (REQ-QUERY-045)

## Phase R.2 — Composition

- [ ] R2.1: Implement the embedding-veto + symbolic-veto pipeline in `(hybrid-match ...)`: call neighbours first, then filter by symbolic match. Preserve neighbour-ordering through the intersection. (REQ-QUERY-040, REQ-QUERY-041)
- [ ] R2.2: Add the `EmbeddingUnavailableError` fallback path: catch, warn on stderr, run pure-symbolic match. (REQ-QUERY-042)
- [ ] R2.3: Empty-result path: assert that no neighbours matching the template returns an empty result, not an error. (REQ-QUERY-043)

## Phase R.3 — Test fixture + docs

- [ ] R3.1: Build the 10-atom "ages" fixture; assert the matching atom appears in top-1 for `(hybrid-match ...)`. (REQ-QUERY-044)
- [ ] R3.2: Extend `docs/booklogic-dsl-reference.md` with §7 "Hybrid queries" covering both grounded atoms with one worked example each. (REQ-QUERY-046)
- [ ] R3.3: Commit `openspec(tier5): hybrid-query change folder (REQ-QUERY-040..046)` once specs land; commit subsequent implementation commits per task group.
