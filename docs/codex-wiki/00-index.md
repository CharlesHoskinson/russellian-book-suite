# Codex wiki - index

This is Codex's persistent notebook across sessions on the BookLogic v0.4 mission. It is version-controlled. Wiki updates ship in the same PR as the work they describe.

## Current phase

**Phase 0.5 — environment + baseline correction.** Phase 0 merged at `1aa51cf`. Phase 0.5 fixes the four environment issues the PR-33 review flagged and locks in the corrected baseline before Phase 1.

## Phase pointers

| # | File | Phase | Status |
|---|---|---|---|
| 0 | (merged) | bootstrap + cross-phase index | merged 1aa51cf |
| 0.5 | this PR | environment + baseline correction | in progress |
| 1 | [01-audit-findings.md](01-audit-findings.md) | deep audit of neurosym-forge + CLJS | not started |
| 2 | (commit in the remediation PR) | fix Critical + Important findings | not started |
| 3 | [02-pr3.5-notes.md](02-pr3.5-notes.md) | port Python ingesters to CLJS | not started |
| 4 | [03-pr4-notes.md](03-pr4-notes.md) | BookLogic active forms | not started |
| 5 | [04-pr5-notes.md](04-pr5-notes.md) | Bermuda migration + real Z3 | not started |
| 6 | [05-pr6-notes.md](05-pr6-notes.md) | osmotic-pressure showcase | not started |
| ∞ | [99-lessons.md](99-lessons.md) | cross-phase lessons | not started |

## Baseline at handoff

Captured 2026-05-15 against origin/main commit `d6ad17b` from the codex worktree, after the Phase 0.5 environment fixes. All counts produced via the brief's canonical invocation: `(cd skills/$s && .venv/Scripts/python.exe -m pytest tests/ -q)`.

| Suite | Tests | Result |
|---|---|---|
| skills/book-knowledge | 141 | pass |
| skills/book-qa | 47 | pass |
| skills/book-compose | 102 | pass |
| skills/neurosym-forge | 155 | pass |
| skills/book-thesis | 16 | pass |
| skills/russellian-style | 110 | pass |
| skills/book-review | 24 | pass |
| skills/review-conductor | 32 | pass |
| verifiers/bermuda | 23 | pass |
| **total** | **650** | **all pass** |

Ruff baseline (130 violations across 9 dirs, all pre-existing). Per directory: `skills/book-knowledge` 44, `skills/book-compose` 35, `skills/neurosym-forge` 16, `skills/book-qa` 6, `skills/book-thesis` 6, `skills/russellian-style` 9, `skills/book-review` 4, `skills/review-conductor` 0, `verifiers/bermuda` 9. Phase 1 audit will triage these as findings (most are likely auto-fixable: 86 with `--fix`, 10 more with `--unsafe-fixes`).

Toolchain on the codex worktree: Node v24.13.0, npm 11.6.2, Python 3.14.2 (system; skill venvs 3.13), rustc 1.95.0, cargo 1.95.0, nbb 1.4.207, ruff 0.15.13. `gh` authenticated to CharlesHoskinson with `repo`, `gist`, `read:org`, `workflow` scopes.

## Update protocol

When a phase starts, change its row to `in progress` and add a `last-updated` date in the per-phase file. When it ends (PR merged), change to `merged` and add the merge SHA.

When resuming after a break, read this file first, then the in-progress per-phase file, then the most recent five entries in `99-lessons.md`.

## Decision log (cross-phase)

- 2026-05-15 - Mission switched from single-agent (Claude implements + reviews) to two-agent (Codex implements, Claude reviews). Spec: `docs/specs/2026-05-15-codex-handoff-design.md`.

## BLOCKED

2026-05-15 — Phase 1 preflight is blocked before audit. `gh auth status` reports that the GitHub token for `CharlesHoskinson` is invalid, so Codex cannot open the required Phase 1 PR. `ruff` is also not on PATH in this shell, although `python -m ruff --version` works and reports `ruff 0.15.13`. Question: should I continue after GitHub CLI authentication is refreshed, using `python -m ruff` for the ruff evidence if `ruff` remains off PATH?
