# Codex GPT-5.5 handoff — design

**Date:** 2026-05-15
**Status:** approved, in progress
**Predecessors:** `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`, `docs/operations/codex-review-protocol.md`, `AGENTS.md`

## Why

Three v0.4 BookLogic PRs have landed (PR-1 EDN at the boundary, PR-2 ingest-trace exporter, PR-3 CLJS compiler for `defsort` / `defpredicate` / `deflift`). Four remain on the mission: PR-3.5 (port Python ingesters to CLJS), PR-4 (active forms `defrule` / `defconstraint` / `defquery` / `defremedy`), PR-5 (Bermuda migration plus real Z3 plus quantitative predicates), PR-6 (osmotic-pressure showcase). Roughly eight workdays of focused implementation remain.

The Claude session that built PR-1 through PR-3 has been the implementer; running it as both implementer and reviewer compresses the feedback loop. Splitting the roles — Codex GPT-5.5 implements, Claude reviews — surfaces blind spots that a single agent's review of its own work cannot catch and frees Claude's context budget for review depth.

## What

Hand Codex GPT-5.5 a six-phase brief covering a deep audit followed by the four remaining PRs. Codex operates the local Codex CLI (≥0.130) in a dedicated worktree, opens one PR per phase, and uses Claude as the PR reviewer via GitHub review comments. Codex keeps a running `docs/codex-wiki/` notebook in the repo for design notes, audit findings, lessons learned, and intermediate state between sessions.

## Out of scope

- Cloud Codex / `codex remote-control`. Local CLI only. The repo is private; the user wants the worktree visible.
- Codex merging its own PRs. The user merges after Claude approves.
- Codex modifying main, force-pushing, or skipping commit hooks.
- Codex writing into `claims/`, `wiki/`, `chapters/`, `book/`, `qa/` of `examples/bermuda-manual/` outside the boundaries set in `CLAUDE.md`. Mission PRs touch `skills/`, `verifiers/`, and the worked-example READMEs only.

## Process flow

```
Phase 0  bootstrap          ── Codex reads guidance, initializes docs/codex-wiki/
Phase 1  audit              ── Codex applies codex-review-protocol scoped to neurosym-forge + CLJS,
                                 writes docs/codex-wiki/01-audit-findings.md (no code changes)
Phase 2  remediation PR     ── Codex fixes Critical and Important findings only.  Claude reviews, user merges.
Phase 3  PR-3.5             ── port Python ingesters to CLJS.        Claude reviews, user merges.
Phase 4  PR-4               ── BookLogic active forms.                Claude reviews, user merges.
Phase 5  PR-5               ── Bermuda migration + real Z3.           Claude reviews, user merges.
Phase 6  PR-6               ── osmotic-pressure showcase.             Claude reviews, user merges.
```

Each phase is one PR. Codex does not start the next phase until the previous PR is merged. The user is in the loop at every merge.

## Codex environment

- Local Codex CLI, version ≥0.130, model GPT-5.5 (Codex's default as of April 2026).
- Worktree at `C:/Users/charl/code/russellian-book-suite-codex` (fresh, off origin/main). Created once at the start of Phase 0.
- Sandbox: `workspace-write` (Codex may write inside the worktree, read outside, but no outbound network beyond `gh` and `npm`).
- Approval: `on-failure` (Codex runs autonomously; surfaces to the user only on shell failures it cannot recover from).
- AGENTS.md at repo root supplies project-doc context automatically. Codex reads CLAUDE.md, `docs/operations/codex-review-protocol.md`, and `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` on its own during Phase 0.

## Authority and constraints

Codex MAY:

- create branches, push to its own branches, open PRs via `gh pr create`
- run any pytest, npm, nbb, cargo, or git command inside the worktree
- create, edit, and delete files inside the worktree
- write into `docs/codex-wiki/` freely

Codex MUST NOT:

- merge, push to main, force-push, rebase shared branches, delete branches it didn't create
- commit with `--no-verify` or bypass any signing or pre-commit hook
- add Co-Authored-By, AI attribution, or AI smells to commits, files, or PR bodies
- make outbound network calls beyond `gh` and `npm install` (no curl, wget, model API calls, telemetry)
- write into `examples/*/claims/`, `examples/*/wiki/`, `examples/*/chapters/`, `examples/*/book/`, `examples/*/qa/` except by invoking the owning skill's CLI

## Wiki / notebook

Codex maintains a markdown notebook at `docs/codex-wiki/`. The notebook is version-controlled and lives in the repo; every wiki update ships in the same PR as the work it describes.

```
docs/codex-wiki/
  00-index.md                — table of contents, last-updated dates, current-phase pointer
  01-audit-findings.md       — Phase 1 output (one document, structured per protocol)
  02-pr3.5-notes.md          — Phase 3 design notes, gotchas, decisions
  03-pr4-notes.md            — Phase 4
  04-pr5-notes.md            — Phase 5
  05-pr6-notes.md            — Phase 6
  99-lessons.md              — cross-phase lessons (append as discovered)
```

Each phase note is structured:

```markdown
# Phase N — <title>

## Context entering this phase
## Decisions made (with rationale)
## Surprises / unexpected complexity
## Bugs found and fixed mid-phase
## Open questions for Claude
## Status: in progress | ready for review | merged
```

The wiki is Codex's persistent memory across sessions. When Codex resumes, it reads `00-index.md` to orient.

## Review handoff

Each PR body ends with this fixed section, populated by Codex:

```markdown
## For reviewer (Claude)

**Phase:** N — <title>
**Spec:** docs/specs/<filename>
**Plan:** docs/plans/<filename> (if any)
**Wiki:** docs/codex-wiki/<filename>

### What to verify
- [bullet] specific behavior the PR claims
- [bullet] specific test added
- [bullet] specific invariant preserved

### What I am uncertain about
- one or two honest doubts; empty if none

### Local QA evidence
- pytest results pasted (counts and key suite names)
- nbb integration test results if applicable
- ruff results
```

Claude reviews via `gh pr review --comment` or by editing review-comment files. Codex polls with `gh pr view <n> --json comments,reviews` and addresses each comment with a fresh commit (never `--amend` on published commits) plus a reply.

## Failure modes anticipated

- **Codex submits a PR without running Phase 8 local QA.** Brief mandates "real QA evidence" in the PR body; Claude rejects PRs missing it.
- **Codex tries to over-scope a phase.** Brief restates "one problem per PR" and lists what each phase MUST NOT touch.
- **Codex's audit produces too many low-severity findings.** Protocol already enforces budget rules; Phase 2 explicitly fixes Critical + Important only, no Minor.
- **Codex regenerates entire files where a small patch suffices.** Brief mandates `apply_patch` with minimal diffs; Claude flags rewrite-as-edit in review.
- **Codex's wiki notes drift from reality.** Wiki updates ship in the same PR as the work; if the PR is right and the wiki is wrong, the wiki is what changes.
- **Codex repeats a fix Claude already requested.** Brief mandates "address each review comment with a fresh commit and reply"; never silently re-push the same change.

## What the user does

- Reads the audit report (Phase 1 deliverable) and signals go / no-go before Phase 2.
- Merges each PR after Claude approves.
- Decides whether to keep, defer, or drop any Minor finding that Codex surfaces but Phase 2 skips.
- Re-engages Codex per phase by re-issuing the bootstrap prompt with `--continue` or a fresh session.

## What Claude does

- Reviews each PR per the PR-review-style memory (severity buckets, gate-replay discipline, no nitpicks).
- Files PR-N-REVIEW.md under `openspec/changes/<phase>/` mirroring each PR.
- Does NOT implement or push commits. If Codex is stuck, Claude posts review guidance and stands down.

## Artifacts produced by this spec

- `docs/handoffs/2026-05-15-codex-deep-review-and-implementation-brief.md` — the full brief Codex works from
- `docs/handoffs/2026-05-15-codex-bootstrap-prompt.md` — the prompt the user pastes into Codex CLI to start each session
- `docs/codex-wiki/00-index.md` — wiki seed, Codex fills the rest

## Success criteria

- All four remaining PRs (PR-3.5, PR-4, PR-5, PR-6) merged, with one prior remediation PR.
- Each PR passes Claude review without Claude rewriting any code.
- `docs/codex-wiki/` contains a coherent narrative of decisions and lessons across the four phases.
- Bermuda's manuscript still builds; its full QA gate still passes after PR-5 lands.
- No regressions in the existing 366 tests (155 neurosym-forge + 141 book-knowledge + 47 book-qa + 23 verifiers/bermuda).
