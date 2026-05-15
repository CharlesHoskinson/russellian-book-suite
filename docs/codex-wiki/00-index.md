# Codex wiki — index

This is Codex's persistent notebook across sessions on the BookLogic v0.4 mission. It is version-controlled. Wiki updates ship in the same PR as the work they describe.

## Current phase

**Phase 0 — bootstrap.** Read AGENTS.md, CLAUDE.md, `docs/operations/codex-review-protocol.md`, `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`, and the brief at `docs/handoffs/2026-05-15-codex-deep-review-and-implementation-brief.md`. Stub the per-phase wiki files below before starting Phase 1.

## Phase pointers

| # | File | Phase | Status |
|---|---|---|---|
| 0 | this file | bootstrap + cross-phase index | in progress |
| 1 | [01-audit-findings.md](01-audit-findings.md) | deep audit of neurosym-forge + CLJS | not started |
| 2 | (commit in the remediation PR) | fix Critical + Important findings | not started |
| 3 | [02-pr3.5-notes.md](02-pr3.5-notes.md) | port Python ingesters to CLJS | not started |
| 4 | [03-pr4-notes.md](03-pr4-notes.md) | BookLogic active forms | not started |
| 5 | [04-pr5-notes.md](04-pr5-notes.md) | Bermuda migration + real Z3 | not started |
| 6 | [05-pr6-notes.md](05-pr6-notes.md) | osmotic-pressure showcase | not started |
| ∞ | [99-lessons.md](99-lessons.md) | cross-phase lessons | not started |

## Update protocol

When a phase starts, change its row to `in progress` and add a `last-updated` date in the per-phase file. When it ends (PR merged), change to `merged` and add the merge SHA.

When resuming after a break, read this file first, then the in-progress per-phase file, then the most recent five entries in `99-lessons.md`.

## Decision log (cross-phase)

- 2026-05-15 — Mission switched from single-agent (Claude implements + reviews) to two-agent (Codex implements, Claude reviews). Spec: `docs/specs/2026-05-15-codex-handoff-design.md`.
