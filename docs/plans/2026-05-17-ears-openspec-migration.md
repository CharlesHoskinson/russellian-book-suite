# EARS + OpenSpec + GitHub Roadmap Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the EARS requirements layer, OpenSpec change directories, and the GitHub roadmap (Milestones + Tracking Issues + draft v0.4.0 Release + Projects v2 board) in one PR before sprint 1 (PR-cleanup) begins. Future sprints execute against `openspec/changes/<sprint>/tasks.md`, not the legacy TDD plan markdown.

**Architecture:** OpenSpec is the single source of truth. Each capability has a steady-state spec at `openspec/specs/<capability>/spec.md` written in EARS. Each sprint is one OpenSpec change at `openspec/changes/<sprint>/` carrying ADD/MODIFY/REMOVE deltas against capability specs. GitHub Milestones mirror OpenSpec changes 1:1; tracking Issues link to the OpenSpec directory; the draft `v0.4.0` Release lists the five Milestones. The existing TDD plans become implementation notes referenced from each sprint's `design.md`.

**Tech Stack:** Markdown, YAML, GitHub CLI (`gh`), GitHub REST + GraphQL APIs. No code changes beyond docs and `.github/` configuration.

---

## Pre-flight

**Hard prerequisite:** PR #39 (branch `plan/booklogic-claude-only-finish`) must be merged to `main` **before** this plan executes. PR #39 lands the five `docs/plans/2026-05-17-booklogic-{cleanup,d2-wiring,pr4,pr5,pr6}.md` files that this plan's spec scaffolds and Task 10.3's link-integrity smoke check assume on disk. Without PR #39 merged, every change `proposal.md` and `design.md` written here links to non-existent paths and Task 10.3 hard-fails.

Verify the prerequisite before starting:

```bash
git ls-files | grep "docs/plans/2026-05-17-booklogic-" | wc -l
```

Expected: `5`. If `0`, stop — merge PR #39 first.

Read these before starting:

- `C:\work\russellian-book-suite\docs\specs\2026-05-17-ears-openspec-roadmap-design.md` — the design this plan implements
- `C:\work\russellian-book-suite\docs\plans\2026-05-17-booklogic-cleanup.md` — source TDD plan for EARS extraction
- `C:\work\russellian-book-suite\docs\plans\2026-05-17-booklogic-d2-wiring.md` — source TDD plan for EARS extraction
- `C:\work\russellian-book-suite\docs\plans\2026-05-17-booklogic-pr4.md` — source TDD plan for EARS extraction
- `C:\work\russellian-book-suite\docs\plans\2026-05-17-booklogic-pr5.md` — source TDD plan for EARS extraction
- `C:\work\russellian-book-suite\docs\plans\2026-05-17-booklogic-pr6.md` — source TDD plan for EARS extraction
- `C:\work\russellian-book-suite\openspec\changes\codex-phase-0\PR-33-REVIEW.md` — the orphan file to delete
- `C:\work\russellian-book-suite\AGENTS.md` — workflow doc to extend
- `https://en.wikipedia.org/wiki/Easy_Approach_to_Requirements_Syntax` — EARS reference
- `https://github.com/Fission-AI/OpenSpec` — OpenSpec reference

**Branch.** All work on `feat/ears-openspec-roadmap`. Create at task 0.1.

**No calendar-time estimates anywhere.** Effort labels (small / long pole / mechanical) are acceptable; "weeks" / "days" are not.

**Test invocation.** This PR ships docs only — no Python or CLJS code changes. Validation is structural (file presence, spec link integrity, GitHub API responses) and lives in shell assertions or one-off Python smoke scripts. No new pytest test files are created in repo tree.

**Commit hygiene.** Terse imperative, no AI attribution, no Co-Authored-By, one problem per commit.

**EARS subset for this PR.**

The five EARS patterns:

| Pattern | Form |
|---|---|
| Ubiquitous | `The <system> shall <requirement>` |
| Event-driven | `When <trigger>, the <system> shall <requirement>` |
| State-driven | `While <state>, the <system> shall <requirement>` |
| Optional feature | `Where <feature>, the <system> shall <requirement>` |
| Unwanted behaviour | `If <condition>, then the <system> shall <requirement>` |

REQ IDs use the form `REQ-<CAPABILITY-SLUG>-<NNN>` where NNN is zero-padded to three digits. Sort lexically. Numbers stable across PRs; renumbering forbidden.

**Capability slugs (eight):**

| Slug | Capability |
|---|---|
| `EDN` | edn-boundary |
| `TRACE` | ingest-trace |
| `DSL` | booklogic-dsl |
| `BERMUDA-RULES` | bermuda-rules |
| `CLJS-ORCH` | cljs-orchestrator |
| `QA-PIPE` | qa-defect-pipeline |
| `VERIFIER-BUILD` | verifier-build |
| `OSMOTIC` | osmotic-pressure-verifier |

---

## File Structure

### Created

```
openspec/
├── README.md                                            NEW (overview + REQ-ID convention)
├── specs/
│   ├── edn-boundary/spec.md                             NEW (steady-state, EARS)
│   ├── ingest-trace/spec.md                             NEW
│   ├── booklogic-dsl/spec.md                            NEW
│   ├── bermuda-rules/spec.md                            NEW
│   ├── cljs-orchestrator/spec.md                        NEW
│   ├── qa-defect-pipeline/spec.md                       NEW
│   ├── verifier-build/spec.md                           NEW
│   └── osmotic-pressure-verifier/spec.md                NEW
└── changes/
    ├── booklogic-cleanup/
    │   ├── proposal.md                                  NEW
    │   ├── design.md                                    NEW
    │   ├── tasks.md                                     NEW
    │   └── specs/
    │       ├── edn-boundary/spec.md                     NEW (delta)
    │       ├── bermuda-rules/spec.md                    NEW (delta)
    │       └── cljs-orchestrator/spec.md                NEW (delta)
    ├── booklogic-d2-wiring/
    │   ├── proposal.md                                  NEW
    │   ├── design.md                                    NEW
    │   ├── tasks.md                                     NEW
    │   └── specs/
    │       ├── ingest-trace/spec.md                     NEW (delta)
    │       └── cljs-orchestrator/spec.md                NEW (delta)
    ├── booklogic-pr4-active-forms/
    │   ├── proposal.md                                  NEW
    │   ├── design.md                                    NEW
    │   ├── tasks.md                                     NEW
    │   └── specs/
    │       ├── booklogic-dsl/spec.md                    NEW (delta)
    │       ├── qa-defect-pipeline/spec.md               NEW (delta)
    │       └── verifier-build/spec.md                   NEW (delta)
    ├── booklogic-pr5-bermuda-migration/
    │   ├── proposal.md                                  NEW
    │   ├── design.md                                    NEW
    │   ├── tasks.md                                     NEW
    │   └── specs/
    │       ├── bermuda-rules/spec.md                    NEW (delta)
    │       ├── verifier-build/spec.md                   NEW (delta)
    │       ├── qa-defect-pipeline/spec.md               NEW (delta)
    │       └── cljs-orchestrator/spec.md                NEW (delta)
    └── booklogic-pr6-osmotic-showcase/
        ├── proposal.md                                  NEW
        ├── design.md                                    NEW
        ├── tasks.md                                     NEW
        └── specs/
            └── osmotic-pressure-verifier/spec.md        NEW (delta)

.github/
├── ISSUE_TEMPLATE/
│   └── openspec-change.yml                              NEW
└── pull_request_template.md                             NEW or EXTEND
```

### Modified

```
AGENTS.md                                                add OpenSpec + EARS workflow section
README.md (repo root)                                    add link to openspec/README.md
```

### Deleted

```
openspec/changes/codex-phase-0/                          DELETE (orphan vestige)
```

### One-shot scripts (not committed)

```
tools/_ears_roadmap_helpers/
├── create_milestones.sh                                 NOT COMMITTED — local helper, ad-hoc
├── create_tracking_issues.sh                            NOT COMMITTED
├── create_draft_release.sh                              NOT COMMITTED
└── create_project_board.sh                              NOT COMMITTED
```

The four shell helpers under `tools/_ears_roadmap_helpers/` are scratch — they document the `gh` commands that ran. They're listed in `.gitignore` per task 0.2 and never reach the index.

---

## Phase 0: Branch + scratch directory

### Task 0.1: Create branch

**Files:**
- None (git operation)

- [ ] **Step 1: Create the branch.**

Run:

```bash
cd C:/work/russellian-book-suite
git checkout main
git pull origin main
git checkout -b feat/ears-openspec-roadmap
```

Expected: `Switched to a new branch 'feat/ears-openspec-roadmap'`.

- [ ] **Step 2: Verify clean state.**

Run: `git status -s`
Expected: empty output.

### Task 0.2: Ignore scratch helpers

**Files:**
- Modify: `C:\work\russellian-book-suite\.gitignore`

- [ ] **Step 1: Append the ignore rule.**

Append to `.gitignore`:

```
# Scratch helpers for one-shot roadmap setup; never committed
tools/_ears_roadmap_helpers/
```

- [ ] **Step 2: Verify.**

Run: `git check-ignore tools/_ears_roadmap_helpers/`
Expected: prints the path (i.e. ignored).

- [ ] **Step 3: Commit.**

```bash
git add .gitignore
git commit -m "gitignore: scratch dir for roadmap helpers"
```

---

## Phase 1: Capability spec stubs

Eight steady-state capability specs. Each starts as a stub with a one-paragraph capability description and zero REQs. REQs accumulate as sprints merge.

### Task 1.1: `openspec/README.md` (overview + REQ convention)

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\README.md`

- [ ] **Step 1: Write the file.**

```markdown
# OpenSpec — russellian-book-suite

This tree holds the spec-driven development surface for the repo, following the
[OpenSpec convention](https://github.com/Fission-AI/OpenSpec).

## Layout

- `specs/<capability>/spec.md` — steady-state truth for each capability. Written in
  [EARS](https://en.wikipedia.org/wiki/Easy_Approach_to_Requirements_Syntax)
  (Easy Approach to Requirements Syntax). Updated by merging spec deltas from
  archived changes.
- `changes/<change-name>/` — in-flight or recently-merged changes. Each contains:
  - `proposal.md` — why + what
  - `design.md` — technical approach
  - `tasks.md` — implementation checklist; each task line cites the REQ IDs it satisfies
  - `specs/<capability>/spec.md` — delta against the steady-state spec (ADD / MODIFY / REMOVE)
- `changes/archive/YYYY-MM-DD-<change-name>/` — archived changes.

## REQ ID convention

`REQ-<CAPABILITY-SLUG>-<NNN>` where NNN is zero-padded. Numbers are stable across
PRs; renumbering is forbidden.

Capability slugs and their full capability names:

| Slug | Capability |
|---|---|
| `EDN` | edn-boundary |
| `TRACE` | ingest-trace |
| `DSL` | booklogic-dsl |
| `BERMUDA-RULES` | bermuda-rules |
| `CLJS-ORCH` | cljs-orchestrator |
| `QA-PIPE` | qa-defect-pipeline |
| `VERIFIER-BUILD` | verifier-build |
| `OSMOTIC` | osmotic-pressure-verifier |

## EARS patterns

| Pattern | Form |
|---|---|
| Ubiquitous | `The <system> shall <requirement>` |
| Event-driven | `When <trigger>, the <system> shall <requirement>` |
| State-driven | `While <state>, the <system> shall <requirement>` |
| Optional feature | `Where <feature>, the <system> shall <requirement>` |
| Unwanted behaviour | `If <condition>, then the <system> shall <requirement>` |

Each REQ in `specs/*/spec.md` carries the pattern label in its heading
(e.g. `### REQ-EDN-001 — Ubiquitous`).

## Workflow

This repo adopts the OpenSpec directory + spec-delta convention manually via `git`
and `gh`. The canonical OpenSpec slash-command interface (`/opsx:propose`,
`/opsx:apply`, `/opsx:archive`) is a Node-based CLI; adopting it is a follow-up
post-v0.4.0 (deferred; tracked as Open Question 6 in the roadmap design doc).
The manual cycle is identical to the CLI's:

1. **Propose.** Create `changes/<change>/proposal.md` (and optionally `design.md`,
   `tasks.md`, `specs/` deltas). Open a draft PR.
2. **Refine.** Iterate until requirements are crisp and spec deltas are agreed.
3. **Execute.** Implement against `tasks.md`. Tests cite REQ IDs in their
   docstring or test name. Each commit references one or more tasks.
4. **Merge.** Squash-merge to `main`. The GitHub Milestone for the change
   auto-closes if the PR is tagged.
5. **Archive.** Move `changes/<change>/` to `changes/archive/YYYY-MM-DD-<change>/`.
   Merge the spec deltas into `specs/<capability>/spec.md`. Publish a GitHub
   Release if the change is a milestone.

## See also

- `docs/specs/2026-05-17-ears-openspec-roadmap-design.md` — the design for this layer.
- `AGENTS.md` § OpenSpec workflow — agent-facing instructions.
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/README.md
git commit -m "openspec: overview + REQ-ID convention"
```

### Task 1.2: Capability spec stub — `edn-boundary`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\specs\edn-boundary\spec.md`

- [ ] **Step 1: Write the stub.**

```markdown
# Capability: edn-boundary

The EDN data interchange between Python, ClojureScript, and Rust components of
the BookLogic pipeline. Owns the `read_edn` / `write_edn` reader/writer pair in
`skills/neurosym-forge/scripts/_edn_reader.py` and `_edn_writer.py`, the
`edn-rs` Rust dep, and the contract that `.edn`-extensioned files on disk
carry real EDN syntax — not JSON-stamped-as-EDN.

Spec deltas accumulate here as sprints merge. The current set is empty;
sprints booklogic-cleanup and booklogic-pr5-bermuda-migration add REQs.

## Requirements

_(none yet — sprints merge ADD deltas here)_
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/specs/edn-boundary/spec.md
git commit -m "openspec: capability stub — edn-boundary"
```

### Task 1.3: Capability spec stub — `ingest-trace`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\specs\ingest-trace\spec.md`

- [ ] **Step 1: Write the stub.**

```markdown
# Capability: ingest-trace

The symbolic event stream exported by `book-knowledge` and consumed by
`verifiers/bermuda` as the Phase-1 input to verification. Replaces the
direct read of `claims/ledger.jsonl` with a typed event sequence
(`source/ingested`, `claim/proposed`, `claim/verified`, `atom/emitted`) at
`<workspace>/analysis/ingest-trace.edn`.

Spec deltas accumulate here as sprints merge. Sprint
booklogic-d2-wiring adds REQs.

## Requirements

_(none yet)_
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/specs/ingest-trace/spec.md
git commit -m "openspec: capability stub — ingest-trace"
```

### Task 1.4: Capability spec stub — `booklogic-dsl`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\specs\booklogic-dsl\spec.md`

- [ ] **Step 1: Write the stub.**

```markdown
# Capability: booklogic-dsl

The BookLogic DSL v0.1: seven EDN form families (`defsort`, `defpredicate`,
`deflift`, `defrule`, `defconstraint`, `defquery`, `defremedy`) lifted into
typed atoms, meander rewrite rules, Z3 axioms, Cozo queries, and
writeback proposals. Owned by the neurosym-forge skill's project template at
`skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl`.

PR-3 shipped the first three (`defsort`, `defpredicate`, `deflift`). Sprint
booklogic-pr4-active-forms adds the remaining four.

## Requirements

_(none yet — PR-3 REQs to backfill in a future maintenance change;
booklogic-pr4-active-forms adds REQs for the four active forms)_
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/specs/booklogic-dsl/spec.md
git commit -m "openspec: capability stub — booklogic-dsl"
```

### Task 1.5: Capability spec stub — `bermuda-rules`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\specs\bermuda-rules\spec.md`

- [ ] **Step 1: Write the stub.**

```markdown
# Capability: bermuda-rules

The Bermuda verifier's BookLogic source set at `verifiers/bermuda/rules/`,
covering the five existing predicates (`parishes`, `named_islands`,
`currency_peg`, `airport_island`, `cedar_binomial`) and four new quantitative
predicates (`population`, `land-area-km2`, `gdp-usd-billion`,
`hospital-beds-kemh`). After full migration, `canonical.rs` is deleted and
`axioms.rs` is the BookLogic codegen output.

Sprints booklogic-cleanup (D1 hygiene on seed.edn + grounded.edn) and
booklogic-pr5-bermuda-migration (full rewrite) add REQs.

## Requirements

_(none yet)_
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/specs/bermuda-rules/spec.md
git commit -m "openspec: capability stub — bermuda-rules"
```

### Task 1.6: Capability spec stub — `cljs-orchestrator`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\specs\cljs-orchestrator\spec.md`

- [ ] **Step 1: Write the stub.**

```markdown
# Capability: cljs-orchestrator

The ClojureScript orchestrator at `verifiers/bermuda/cljs-orchestrator/`,
comprising six modules (`bridge`, `core`, `ir`, `nl_to_fol`, `phases`,
`unify`) plus the `shadow-cljs` build and test targets. Owns the CLI
dispatch (`translate` / `verify` / `typeset`), the malli schemas for
`Atom`, `Formula`, `Claim`, `Verdict`, the meander `Claim → Formula`
rewrite, and the napi bridge to the Rust verifier.

Sprints booklogic-cleanup (test harness + bug fix),
booklogic-d2-wiring (event-aware translate), and
booklogic-pr5-bermuda-migration (verify subcommand on real Z3) add REQs.

## Requirements

_(none yet)_
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/specs/cljs-orchestrator/spec.md
git commit -m "openspec: capability stub — cljs-orchestrator"
```

### Task 1.7: Capability spec stub — `qa-defect-pipeline`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\specs\qa-defect-pipeline\spec.md`

- [ ] **Step 1: Write the stub.**

```markdown
# Capability: qa-defect-pipeline

The book-qa defect gate: D1-D8 deterministic linter, D9-D12 metabook
defects from book-thesis, D13 verifier-unsat defects from the Bermuda /
osmotic-pressure verifiers, the C1-C15 chapter agent swarm, and the
sentinel/healer/writeback loop. Owned by `skills/book-qa/`.

Sprints booklogic-pr4-active-forms (writeback adapter for BookLogic
remedies) and booklogic-pr5-bermuda-migration (D13 fire end-to-end) add
REQs.

## Requirements

_(none yet)_
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/specs/qa-defect-pipeline/spec.md
git commit -m "openspec: capability stub — qa-defect-pipeline"
```

### Task 1.8: Capability spec stub — `verifier-build`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\specs\verifier-build\spec.md`

- [ ] **Step 1: Write the stub.**

```markdown
# Capability: verifier-build

The Rust verifier build pipeline: cargo manifest, `edn-rs` / `z3` / `cozo`
/ `egg` dependencies, the napi-rs node addon, and the CI workflows that
gate real Z3 builds on `ubuntu-latest`. Covers `verifiers/bermuda/rust-verifier/`
and the analogous tree in scaffolded projects under
`skills/neurosym-forge/assets/project-template/`.

Sprints booklogic-pr4-active-forms (`cargo check` codegen gate) and
booklogic-pr5-bermuda-migration (`cargo build` + Z3 link CI gate) add
REQs.

## Requirements

_(none yet)_
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/specs/verifier-build/spec.md
git commit -m "openspec: capability stub — verifier-build"
```

### Task 1.9: Capability spec stub — `osmotic-pressure-verifier`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\specs\osmotic-pressure-verifier\spec.md`

- [ ] **Step 1: Write the stub.**

```markdown
# Capability: osmotic-pressure-verifier

The chemistry-domain showcase verifier at `verifiers/osmotic_pressure/`,
demonstrating BookLogic on a non-book domain. Verifies the van 't Hoff
osmotic-pressure equation (`π = i·M·R·T`) against clean and doctored
fixture ledgers using the `~=` (approximate equality) operator with a 3%
relative tolerance.

Sprint booklogic-pr6-osmotic-showcase creates this capability.

## Requirements

_(none yet)_
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/specs/osmotic-pressure-verifier/spec.md
git commit -m "openspec: capability stub — osmotic-pressure-verifier"
```

---

## Phase 2: OpenSpec change scaffolds

For each of the five sprints, scaffold the four-file shape. Tasks 2.1-2.5
create the `proposal.md`, `design.md`, and an empty `tasks.md` for one
sprint each. Phase 3 fills in the spec deltas. Phase 7 fills in
`tasks.md` from the existing TDD plans.

The `proposal.md` for each sprint is short (~80-120 lines): WHY + WHAT
+ scope + acceptance. The `design.md` is a thin pointer to the existing
TDD plan ("see the detailed implementation notes at
`docs/plans/2026-05-17-booklogic-<sprint>.md`") plus any high-level
architectural commentary not already in the design spec.

### Task 2.1: `booklogic-cleanup` change scaffold

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-cleanup\proposal.md`
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-cleanup\design.md`
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-cleanup\tasks.md`

- [ ] **Step 1: Write `proposal.md`.**

```markdown
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
```

- [ ] **Step 2: Write `design.md`.**

```markdown
# Design: booklogic-cleanup

## Architecture pointer

Full architectural detail and TDD-shaped task instructions live in the
implementation-notes plan at:

`docs/plans/2026-05-17-booklogic-cleanup.md`

That file walks each of the 20 tasks with five-step TDD instructions
(failing test → run+FAIL → implement → run+PASS → commit), exact file
paths, full source for each new file, and the exact `Edit` calls for
each modification.

## Why a separate plan file

The TDD plan is verbose by design — it ships as instructions for a Claude
session with zero context. The OpenSpec `tasks.md` in this directory is
the lightweight checklist version; agents executing the change consult
the TDD plan when they need exact source bodies.

## Key decisions locked in the TDD plan

- AGENTS.md doesn't actually contain "two-agent" language; the cleanup
  edit is minimal accordingly.
- Only two `2026-05-15-codex-*.md` handoff files exist (not four).
- The `nl_to_fol` bug is the `:keyword`-schema collision against the
  `~?pred` binding in the meander rule.
- The `shadow-cljs :test` target uses `:node-test` (Node-driven
  `cljs.test`), not browser-driven testing.

## Open questions

None — fully designed.
```

- [ ] **Step 3: Write an empty `tasks.md`.**

```markdown
# Tasks: booklogic-cleanup

This file is the executor's checklist. Each task line cites the REQ IDs it
satisfies in parentheses. Source bodies, full commands, and TDD steps live
in the implementation-notes plan at
`docs/plans/2026-05-17-booklogic-cleanup.md` — task numbers in that plan
correspond 1:1 with task numbers here.

## Phase 1 — Strip Codex scaffolding

- [ ] T1.1: Create branch `feat/booklogic-cleanup`.
- [ ] T1.2: Delete `docs/codex-wiki/`. (no REQ)
- [ ] T1.3: Delete `docs/handoffs/2026-05-15-codex-*.md`. (no REQ)
- [ ] T1.4: Delete `docs/specs/2026-05-15-codex-handoff-design.md`. (no REQ)
- [ ] T1.5: Delete `openspec/changes/codex-phase-0/`. (no REQ; superseded by Phase 0 of the EARS migration)
- [ ] T1.6: Edit `AGENTS.md` — drop the minimal two-agent language. (no REQ)
- [ ] T1.7: Strip PR-3.5 references from `docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md`. (no REQ)
- [ ] T1.8: Run grep gate; assert no `codex` matches in active docs. (no REQ)

## Phase 2 — D1 data hygiene

- [ ] T2.1: Write failing test asserting real-EDN round-trip on `seed.edn` and `grounded.edn`. (REQ-EDN-010, REQ-EDN-011)
- [ ] T2.2: Convert `verifiers/bermuda/rules/seed.edn` to real EDN. (REQ-EDN-010, REQ-BERMUDA-RULES-001)
- [ ] T2.3: Convert `verifiers/bermuda/rules/grounded.edn` to real EDN. (REQ-EDN-011, REQ-BERMUDA-RULES-002)

## Phase 3 — CLJS test harness

- [ ] T3.1: Add `shadow-cljs :test` node-test target. (REQ-CLJS-ORCH-001)
- [ ] T3.2: Tests for `bermuda.unify`. (REQ-CLJS-ORCH-002)
- [ ] T3.3: Tests for `bermuda.ir` (malli round-trips). (REQ-CLJS-ORCH-003)
- [ ] T3.4: Tests for `bermuda.nl-to-fol` (rule shape; the failing case for the bug). (REQ-CLJS-ORCH-004)
- [ ] T3.5: Tests for `bermuda.phases` (pre/post contract violations). (REQ-CLJS-ORCH-005)
- [ ] T3.6: Tests for `bermuda.bridge` (stub addon; call shapes). (REQ-CLJS-ORCH-006)
- [ ] T3.7: Tests for `bermuda.core` (CLI dispatch). (REQ-CLJS-ORCH-007)

## Phase 4 — Fix `nl_to_fol` bug

- [ ] T4.1: Fix the schema collision in `claim->formula`; reuse the failing test from T3.4. (REQ-CLJS-ORCH-008)

## Phase 5 — CI integration

- [ ] T5.1: Add `cljs-bermuda-test` job to `.github/workflows/ci.yml`. (REQ-CLJS-ORCH-009)

## Phase 6 — Smoke + PR

- [ ] T6.1: Full sweep; scaffold a fresh project to confirm nothing regressed. (no REQ — meta)
- [ ] T6.2: Push branch, open PR with body referencing this change directory. (no REQ — meta)
```

- [ ] **Step 4: Commit.**

```bash
git add openspec/changes/booklogic-cleanup/
git commit -m "openspec: booklogic-cleanup change scaffold"
```

### Task 2.2: `booklogic-d2-wiring` change scaffold

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-d2-wiring\proposal.md`
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-d2-wiring\design.md`
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-d2-wiring\tasks.md`

- [ ] **Step 1: Write `proposal.md`.**

```markdown
# Change: booklogic-d2-wiring

**Sprint:** 2 of 5
**Branch:** `feat/booklogic-d2-wiring`
**GitHub Milestone:** `booklogic-d2-wiring`

## Why

PR-2 of the v0.4 mission shipped `skills/book-knowledge/scripts/export_symbolic_trace.py`,
which emits `analysis/ingest-trace.edn` — a symbolic event stream of
ingestion events. But no verifier consumes it. `verifiers/bermuda/scripts/run_verification.py`
still reads `claims/ledger.jsonl` directly, defeating the purpose of the
trace artifact.

D2 of the mission spec is therefore half-done. This change closes it:
the Bermuda verifier reads the trace when present, falls back to the
legacy ledger when not, and the CLJS `translate` accepts either claim-list
or event-stream input.

## What

- `run_verification.py` Phase-1 reads `analysis/ingest-trace.edn` if present,
  falls back to `claims/ledger.jsonl`.
- CLJS `bermuda.core.translate` dispatches on event-head when given the
  event-stream shape, preserving the legacy claim-list path.
- One integration test synthesises a trace and asserts the verifier emits
  the expected atoms.

## Capabilities touched

- `ingest-trace` — ADD requirements for the consume-side contract
- `cljs-orchestrator` — ADD requirement for event-aware `translate`

## Implementation notes

See `docs/plans/2026-05-17-booklogic-d2-wiring.md` (5 phases, 11 tasks).

## Acceptance

- `run_verification.py` exits 0 against a fresh workspace that has
  `analysis/ingest-trace.edn` but no `claims/ledger.jsonl`
- Existing legacy-path tests still pass
- The Bermuda smoke CI pipeline is still green
- All REQ IDs added are test-covered
```

- [ ] **Step 2: Write `design.md`.**

```markdown
# Design: booklogic-d2-wiring

## Architecture pointer

Full TDD-shaped detail at `docs/plans/2026-05-17-booklogic-d2-wiring.md`.

## Key decisions

- The Python side dispatches via path existence (`analysis/ingest-trace.edn`
  takes precedence) rather than a config flag — automatic migration.
- The CLJS side keeps the existing `claim->formula` meander rule unchanged
  as a private helper; a new `event->formula` dispatcher selects it for
  legacy claim-list input.
- A new malli schema `ClaimOrEvent` relaxes the `phases/translate` pre-contract.
- Unknown event heads are opaque (skip), not errors — forward compatibility
  for future event kinds.

## Open questions

None.
```

- [ ] **Step 3: Write `tasks.md`.**

```markdown
# Tasks: booklogic-d2-wiring

See `docs/plans/2026-05-17-booklogic-d2-wiring.md` for full TDD steps. Task numbers correspond 1:1.

## Phase 1 — Python trace-aware Phase-1 reader

- [ ] T1.1: Failing test for trace-only workspace; verifier loads N atoms. (REQ-TRACE-001)
- [ ] T1.2: Implement `run_verification.py` trace dispatch. (REQ-TRACE-001, REQ-TRACE-002)

## Phase 2 — Legacy fallback

- [ ] T2.1: Legacy-only workspace test passes. (REQ-TRACE-003)

## Phase 3 — CLJS event-aware translate

- [ ] T3.1: `shadow-cljs :test` already exists from cleanup; if not, add. (REQ-CLJS-ORCH-001)
- [ ] T3.2: `nl_to_fol` test cases for each event head. (REQ-CLJS-ORCH-010)
- [ ] T3.3: Implement `event->formula` dispatcher. (REQ-CLJS-ORCH-010, REQ-CLJS-ORCH-011)

## Phase 4 — Integration sweep

- [ ] T4.1: End-to-end test with synthesised trace. (REQ-TRACE-004)
- [ ] T4.2: Regression sweep — all Bermuda Python tests. (no REQ — meta)
- [ ] T4.3: Regression sweep — CLJS test suite. (no REQ — meta)
- [ ] T4.4: Confirm Bermuda smoke pipeline still green. (no REQ — meta)

## Phase 5 — Smoke + PR

- [ ] T5.1: Full sweep. (no REQ — meta)
- [ ] T5.2: Push + open PR. (no REQ — meta)
```

- [ ] **Step 4: Commit.**

```bash
git add openspec/changes/booklogic-d2-wiring/
git commit -m "openspec: booklogic-d2-wiring change scaffold"
```

### Task 2.3: `booklogic-pr4-active-forms` change scaffold

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr4-active-forms\proposal.md`
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr4-active-forms\design.md`
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr4-active-forms\tasks.md`

- [ ] **Step 1: Write `proposal.md`.**

```markdown
# Change: booklogic-pr4-active-forms

**Sprint:** 3 of 5
**Branch:** `feat/booklogic-pr4`
**GitHub Milestone:** `booklogic-pr4-active-forms`

## Why

The BookLogic compiler shipped `defsort`, `defpredicate`, `deflift` in
PR-3 — the passive declarative forms. The four active forms (`defrule`,
`defconstraint`, `defquery`, `defremedy`) are absent. Without them,
Bermuda cannot be migrated off the hand-coded `canonical.rs` + Cozo stub
+ ad-hoc writeback.

## What

- Extend `booklogic.cljs.tmpl` with the four expanders.
- Codegen `rust-verifier/src/axioms.rs` from `defconstraint`.
- Wire real Cozo into `kg.rs` as the `defquery` backend.
- Teach `book-qa.scripts.propose_writeback.py` to accept BookLogic remedies.
- Per-form compiler tests + axioms shape tests + Cozo query smoke +
  remedy adapter test.

## Pre-declared split

This is the long pole. The change is structured as two tracks:

- **Track A:** Phases 1, 2 (defrule + defconstraint + axioms codegen). Pure Z3.
- **Track B:** Phases 3, 4 (defquery + Cozo + defremedy + writeback).

Decision point after Phase 2 acceptance. If Cozo build is non-trivial
or executor needs to ship before Track B is testable, split into
`booklogic-pr4a-defconstraint` and `booklogic-pr4b-defquery-defremedy`.
The split criteria are documented in `design.md`.

## Capabilities touched

- `booklogic-dsl` — ADD requirements for the four active forms
- `qa-defect-pipeline` — ADD requirement for BookLogic remedy acceptance
- `verifier-build` — ADD requirement for axioms.rs codegen + cargo check gate

## Implementation notes

See `docs/plans/2026-05-17-booklogic-pr4.md` — long, 7 phases, including the
pre-declared a/b split.

## Acceptance

- All four expanders have passing compiler tests
- `axioms.rs` generated from a sample project passes `cargo check`
- `kg.rs` Cozo path returns expected rows for one fixture query
- `propose_writeback` emits a remedy-driven transition for a fixture verdict
- Mission spec § D4 footer updated
- All REQ IDs added are test-covered
```

- [ ] **Step 2: Write `design.md`.**

```markdown
# Design: booklogic-pr4-active-forms

## Architecture pointer

Full TDD-shaped detail at `docs/plans/2026-05-17-booklogic-pr4.md`.

## Pre-declared a/b split

Decision point: after Phase 2 acceptance (defconstraint codegen + `cargo check`
gate green). Split into PR-4a + PR-4b if **any** of:

1. `cargo check --features kg` fails with a Cozo dependency error that
   doesn't resolve in a focused investigation block.
2. Cozo dyn-link API differs from documented `cozo = "0.7"` in a way that
   requires upstream patching.
3. Track A is fully green and the executor needs to ship before Track B
   is testable.

Otherwise: one PR-4.

## Open-question resolution

- OQ #1 (`~=` operator): in scope, Phase 2.3 `_emit_approx_block`.
- OQ #4 (bidirectional traceability): solved via generated
  `rules/axioms-tracker-map.edn` (keyed by tracker name).
- OQ #5 (Z3 bundled on Windows): deferred to PR-5; PR-4 uses `cargo check`
  not `cargo build` so the C++ link is skipped.

## Cargo manifest path

`<project>/rust-verifier/Cargo.toml` (template-instantiated).
```

- [ ] **Step 3: Write `tasks.md`.**

```markdown
# Tasks: booklogic-pr4-active-forms

See `docs/plans/2026-05-17-booklogic-pr4.md` for full TDD steps. Phase /
task numbers correspond 1:1.

## Track A

### Phase 1 — `defrule` expander
- [ ] T1.1: Failing CLJS test for defrule expansion. (REQ-DSL-010)
- [ ] T1.2: Implement `defrule` expander. (REQ-DSL-010)

### Phase 2 — `defconstraint` + `axioms.rs` codegen
- [ ] T2.1: Failing CLJS test for defconstraint intermediate edn shape. (REQ-DSL-020)
- [ ] T2.2: Implement defconstraint expander. (REQ-DSL-020)
- [ ] T2.3: Failing Python test for `axioms.rs` codegen output. (REQ-VERIFIER-BUILD-010, REQ-DSL-021)
- [ ] T2.4: Implement Python codegen (incl. `~=` approx-equality desugaring). (REQ-VERIFIER-BUILD-010, REQ-DSL-021, REQ-DSL-022)
- [ ] T2.5: Failing test for generated tracker-map. (REQ-DSL-023)
- [ ] T2.6: Implement tracker-map emit. (REQ-DSL-023)
- [ ] T2.7: `cargo check --features smt` gate; ship as `feat/booklogic-pr4a` if splitting. (REQ-VERIFIER-BUILD-011)

### Decision point — split or continue

## Track B

### Phase 3 — `defquery` + Cozo `kg.rs`
- [ ] T3.1: Failing CLJS test for defquery expansion. (REQ-DSL-030)
- [ ] T3.2: Implement defquery expander. (REQ-DSL-030)
- [ ] T3.3: Replace `kg.rs` stub with Cozo backend. (REQ-VERIFIER-BUILD-020)
- [ ] T3.4: End-to-end query smoke. (REQ-DSL-031, REQ-VERIFIER-BUILD-021)
- [ ] T3.5: `cargo check --features kg` gate. (REQ-VERIFIER-BUILD-022)

### Phase 4 — `defremedy` + writeback adapter
- [ ] T4.1: Failing CLJS test for defremedy expansion. (REQ-DSL-040)
- [ ] T4.2: Implement defremedy expander. (REQ-DSL-040)
- [ ] T4.3: Failing Python test for `propose_writeback` remedy ingestion. (REQ-QA-PIPE-010)
- [ ] T4.4: Implement `propose_writeback` BookLogic adapter. (REQ-QA-PIPE-010, REQ-QA-PIPE-011)
- [ ] T4.5: `:requires :human-review` blocks auto-apply test. (REQ-QA-PIPE-012)

## Phase 5 — Mission spec footer

- [ ] T5.1: Update mission spec § D4 with merge-SHA placeholder. (no REQ — meta)

## Phase 6 — Full template smoke

- [ ] T6.1: Scaffold fresh project, declare one of each form, run pipeline. (no REQ — meta)

## Phase 7 — PR

- [ ] T7.1: Push + open PR. (no REQ — meta)
```

- [ ] **Step 4: Commit.**

```bash
git add openspec/changes/booklogic-pr4-active-forms/
git commit -m "openspec: booklogic-pr4-active-forms change scaffold"
```

### Task 2.4: `booklogic-pr5-bermuda-migration` change scaffold

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr5-bermuda-migration\proposal.md`
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr5-bermuda-migration\design.md`
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr5-bermuda-migration\tasks.md`

- [ ] **Step 1: Write `proposal.md`.**

```markdown
# Change: booklogic-pr5-bermuda-migration

**Sprint:** 4 of 5
**Branch:** `feat/booklogic-pr5`
**GitHub Milestone:** `booklogic-pr5-bermuda-migration`

## Why

Bermuda still runs the pre-BookLogic v0.2 pipeline: `canonical.rs` is
hand-edited, `predicates.edn` is hand-written, the four quantitative
predicates promised by the mission (`population`, `land-area-km2`,
`gdp-usd-billion`, `hospital-beds-kemh`) are absent, there is no real
Z3 build in CI, and the ch-02 parish-count drift (ledger says 9, prose
says 8) does not fire a D13 ticket end-to-end. The headline mission
deliverable (D4: Bermuda migrated; D13 fires on real Z3) is unmet.

## What

- Rewrite `verifiers/bermuda/rules/` as BookLogic source: `sorts.edn`,
  `predicates.edn`, `lifts.edn`, `rules.edn`, `constraints.edn`,
  `queries.edn`, `remedies.edn`.
- Append the four quantitative claims to
  `examples/bermuda-manual/claims/ledger.jsonl`.
- Delete `canonical.rs`; check in generated `axioms.rs`.
- `prose_patterns.py` becomes a thin loader of the lift-generated regex table.
- Add `bermuda-z3-build` + `bermuda-z3-verify` CI jobs on `ubuntu-latest`.
- End-to-end smoke fires D13 against the ch-02 drift at
  `examples/bermuda-manual/book/releases/6.0.0/chapter-bundles/ch-02-v6/draft.md:44`.
- `test_run_verification.py` drops `stub_verifier=True` default.

## Capabilities touched

- `bermuda-rules` — ADD/MODIFY requirements for the BookLogic-sourced rules
- `verifier-build` — ADD requirement for real Z3 cargo build on `ubuntu-latest`
- `qa-defect-pipeline` — ADD requirement for end-to-end D13 fire on parish drift
- `cljs-orchestrator` — ADD requirement for `verify` subcommand on real verdicts

## Implementation notes

See `docs/plans/2026-05-17-booklogic-pr5.md` (9 phases, ~16 tasks).

## Acceptance

- BookLogic compiler on Bermuda's `rules/` produces `axioms.rs`
  byte-identical to the committed file
- `cargo build` of Bermuda verifier succeeds on `ubuntu-latest` CI
- Real Z3 run against Bermuda returns `:unsat` with ch-02 prose-claim id
  in the unsat core
- `book-qa` emits one D13 critical ticket against the ch-02 drift
- All 23 Bermuda Python tests still pass
- All REQ IDs added are test-covered
```

- [ ] **Step 2: Write `design.md`.**

```markdown
# Design: booklogic-pr5-bermuda-migration

## Architecture pointer

Full TDD-shaped detail at `docs/plans/2026-05-17-booklogic-pr5.md`.

## Key decisions

- Five existing Bermuda predicates (`parishes`, `named_islands`, `currency_peg`,
  `airport_island`, `cedar_binomial`) migrate verbatim to BookLogic source.
- Four new quantitative predicates added: `population`, `land-area-km2`,
  `gdp-usd-billion`, `hospital-beds-kemh`.
- `canonical.rs` asserts five facts today: parishes=9, islands=181, BMD/USD
  parity, L. F. Wade on St. David's, cedar = Juniperus bermudiana. Each
  becomes a `defconstraint` in `rules/constraints.edn`.
- Z3 build canonical gate: `ubuntu-latest` CI with `bundled` Z3. Local
  Windows build best-effort; if it fails, capture diagnostics and continue.
- The ch-02 drift target is line 44 of
  `examples/bermuda-manual/book/releases/6.0.0/chapter-bundles/ch-02-v6/draft.md`
  ("Richard Norwood divided the colony into eight parishes"). The ledger
  claim `clm-2026-000008` says nine.

## Risks

- Z3 bundled build cold-builds C++ from source on CI's first run.
  `Swatinem/rust-cache@v2` primes for subsequent runs.
- PR-4's `defconstraint` codegen must emit `axioms.rs` deterministically;
  if it doesn't, Phase 2 surfaces the gap.

## Open questions

None.
```

- [ ] **Step 3: Write `tasks.md`.**

```markdown
# Tasks: booklogic-pr5-bermuda-migration

See `docs/plans/2026-05-17-booklogic-pr5.md` for full TDD steps. Phase /
task numbers correspond 1:1.

## Phase 1 — Author Bermuda BookLogic source

- [ ] T1.1: `rules/sorts.edn`. (REQ-BERMUDA-RULES-010)
- [ ] T1.2: `rules/predicates.edn` (5 existing + 4 new). (REQ-BERMUDA-RULES-011, REQ-BERMUDA-RULES-012)
- [ ] T1.3: `rules/lifts.edn` (every regex from `prose_patterns.py`). (REQ-BERMUDA-RULES-013)
- [ ] T1.4: `rules/rules.edn`. (REQ-BERMUDA-RULES-014)
- [ ] T1.5: `rules/constraints.edn` (5 existing facts + 4 new). (REQ-BERMUDA-RULES-015, REQ-BERMUDA-RULES-016)
- [ ] T1.6: `rules/queries.edn` (at least one Cozo query). (REQ-BERMUDA-RULES-017)
- [ ] T1.7: `rules/remedies.edn` (at least one remedy). (REQ-BERMUDA-RULES-018)

## Phase 2 — Codegen + lockstep

- [ ] T2.1: Compile BookLogic, generate `axioms.rs`. (REQ-VERIFIER-BUILD-030)
- [ ] T2.2: `test_axioms_lockstep.py` — codegen output stable. (REQ-VERIFIER-BUILD-031)
- [ ] T2.3: Delete `canonical.rs`. (REQ-BERMUDA-RULES-019)
- [ ] T2.4: Rewrite `prose_patterns.py` as a thin loader of the lift-generated table. (REQ-BERMUDA-RULES-020)

## Phase 3 — Quantitative claims in ledger

- [ ] T3.1: Append 4 quantitative claims to `examples/bermuda-manual/claims/ledger.jsonl`. (REQ-BERMUDA-RULES-021)

## Phase 4 — Local Z3 build (best-effort)

- [ ] T4.1: `cargo build --features z3,bundled` locally; capture diagnostics if it fails. (no REQ — meta)

## Phase 5 — CI Z3 build

- [ ] T5.1: Add `bermuda-z3-build` job. (REQ-VERIFIER-BUILD-040)
- [ ] T5.2: Add `bermuda-z3-verify` job. (REQ-VERIFIER-BUILD-041, REQ-QA-PIPE-020)

## Phase 6 — End-to-end D13 smoke

- [ ] T6.1: Author ch-02 drift fixture. (REQ-QA-PIPE-021)
- [ ] T6.2: Run full verifier; assert `:unsat` with claim id in core. (REQ-QA-PIPE-022)
- [ ] T6.3: Assert `book-qa` emits D13 critical ticket. (REQ-QA-PIPE-023)

## Phase 7 — `test_run_verification.py` migration

- [ ] T7.1: Drop `stub_verifier=True` default; CI uses real Z3. (REQ-VERIFIER-BUILD-042)

## Phase 8 — Mission spec footer

- [ ] T8.1: Update mission spec § D4 with merge-SHA placeholder. (no REQ — meta)

## Phase 9 — PR

- [ ] T9.1: Push + open PR. (no REQ — meta)
```

- [ ] **Step 4: Commit.**

```bash
git add openspec/changes/booklogic-pr5-bermuda-migration/
git commit -m "openspec: booklogic-pr5-bermuda-migration change scaffold"
```

### Task 2.5: `booklogic-pr6-osmotic-showcase` change scaffold

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr6-osmotic-showcase\proposal.md`
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr6-osmotic-showcase\design.md`
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr6-osmotic-showcase\tasks.md`

- [ ] **Step 1: Write `proposal.md`.**

```markdown
# Change: booklogic-pr6-osmotic-showcase

**Sprint:** 5 of 5 (final)
**Branch:** `feat/booklogic-pr6`
**GitHub Milestone:** `booklogic-pr6-osmotic-showcase`
**On merge:** publish `v0.4.0` GitHub Release.

## Why

The mission promises a non-book domain to prove BookLogic is reusable
beyond the Bermuda manual. None exists. Without a chemistry-domain
showcase, the "generic DSL" claim is unsupported.

## What

- Greenfield `verifiers/osmotic_pressure/` scaffolded entirely via the
  BookLogic compiler (no hand-edits beyond what BookLogic generates).
- `rules/sorts.edn`, `predicates.edn`, `lifts.edn`, `constraints.edn`
  encoding the van 't Hoff equation `π = i·M·R·T` with `~=` 3% tolerance.
- Two fixture ledgers:
  - `claims_clean.jsonl` — i=2, M=0.154, T=298.15, π=780202.5 → expect `:sat`
  - `claims_doctored.jsonl` — i=1, same M/T/π → expect `:unsat` with the i=1
    claim id in the unsat core
- New `osmotic-pressure-smoke` CI job.
- On merge: publish `v0.4.0`.

## Capabilities touched

- `osmotic-pressure-verifier` — ADD (this capability is created by this change)

## Implementation notes

See `docs/plans/2026-05-17-booklogic-pr6.md` (8 phases).

## Acceptance

- Scaffolded project builds with zero hand-edits
- Both fixture verdicts match expected
- `~=` codegen exercised end-to-end
- CI smoke job is green
- All REQ IDs added are test-covered
```

- [ ] **Step 2: Write `design.md`.**

```markdown
# Design: booklogic-pr6-osmotic-showcase

## Architecture pointer

Full TDD-shaped detail at `docs/plans/2026-05-17-booklogic-pr6.md`.

## Dependencies

- PR-4 must have shipped `defconstraint` + `axioms.rs` codegen + the
  `~=` operator (with the mission spec's relative-tolerance semantics).
- PR-5 must have established the `ubuntu-latest` Z3 CI build path; PR-6
  follows the same approach.

## Verdict-shape note

The current `verifiers/bermuda/rust-verifier/src/ir.rs::emit_verdict`
writes `:status`; PR-4's revamped emitter writes `:verdict`. The PR-6
smoke harness accepts both keys to avoid coupling to a specific emit
order.

## Open questions

None.
```

- [ ] **Step 3: Write `tasks.md`.**

```markdown
# Tasks: booklogic-pr6-osmotic-showcase

See `docs/plans/2026-05-17-booklogic-pr6.md` for full TDD steps. Phase /
task numbers correspond 1:1.

## Phase 1 — Scaffold

- [ ] T1.1: Run `scaffold_project --name "Osmotic pressure" --slug osmotic_pressure`. (REQ-OSMOTIC-001)

## Phase 2 — BookLogic source

- [ ] T2.1: `rules/sorts.edn` — `:solution`. (REQ-OSMOTIC-010)
- [ ] T2.2: `rules/predicates.edn` — four predicates. (REQ-OSMOTIC-011)
- [ ] T2.3: `rules/lifts.edn` — at least one lift. (REQ-OSMOTIC-012)
- [ ] T2.4: `rules/constraints.edn` — van 't Hoff with `~=` 3% tolerance. (REQ-OSMOTIC-013)

## Phase 3 — Fixture ledgers

- [ ] T3.1: `claims_clean.jsonl`. (REQ-OSMOTIC-020)
- [ ] T3.2: `claims_doctored.jsonl`. (REQ-OSMOTIC-021)

## Phase 4 — Codegen + build

- [ ] T4.1: Compile BookLogic to `axioms.rs`. (REQ-OSMOTIC-030)
- [ ] T4.2: `cargo build --features z3,bundled` (Linux canonical). (REQ-OSMOTIC-031)

## Phase 5 — End-to-end smoke

- [ ] T5.1: Clean ledger → `:sat`. (REQ-OSMOTIC-040)
- [ ] T5.2: Doctored ledger → `:unsat` with i=1 claim id in core. (REQ-OSMOTIC-041)

## Phase 6 — CI

- [ ] T6.1: Add `osmotic-pressure-smoke` job. (REQ-OSMOTIC-050)

## Phase 7 — Mission spec footer

- [ ] T7.1: Update mission spec § D5 with merge-SHA placeholder. (no REQ — meta)

## Phase 8 — PR + v0.4.0 Release

- [ ] T8.1: Push, open PR. (no REQ — meta)
- [ ] T8.2: On merge, publish v0.4.0 GitHub Release. (no REQ — meta)
```

- [ ] **Step 4: Commit.**

```bash
git add openspec/changes/booklogic-pr6-osmotic-showcase/
git commit -m "openspec: booklogic-pr6-osmotic-showcase change scaffold"
```

---

## Phase 3: EARS extraction — spec deltas per sprint

Each task here adds the spec delta files under `openspec/changes/<sprint>/specs/<capability>/spec.md`.
Delta files are short — typically 5-15 REQs each. The full REQ set across
all five sprints sums to ~50-80 REQs (less than the spec's "~125" estimate;
the actual count surfaces from extraction).

The format for a delta file:

```markdown
# Capability delta: <capability> — change: <change-name>

## ADD

### REQ-<SLUG>-<NNN> — <Pattern>

<EARS sentence>

**Rationale:** <one line>
**Tested by:** <test path + name> (added in <task ID>)

## MODIFY

(none, or list)

## REMOVE

(none, or list)
```

REQ numbering: capability counters increment monotonically across all
sprints. For sprint 1 (`booklogic-cleanup`), the EDN counter starts at
010 (leaving 001-009 reserved for PR-1/PR-3 backfill in a future change).
Same convention for every capability.

### Task 3.1: Delta — `booklogic-cleanup/specs/edn-boundary/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-cleanup\specs\edn-boundary\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: edn-boundary — change: booklogic-cleanup

## ADD

### REQ-EDN-010 — Ubiquitous

The `verifiers/bermuda/rules/seed.edn` file shall be valid EDN: keyword keys
are written as `:foo` (not `":foo"`), and the file round-trips through
`skills/neurosym-forge/scripts/_io.read_edn_file` to a structure where every
key is a `Keyword` instance.

**Rationale:** PR-1's boundary fix migrated the Python/Rust code paths but
missed the static data files. CLJS readers parse `":int"` as a string, not
a keyword, silently breaking downstream meander matches.
**Tested by:** `verifiers/bermuda/tests/test_rules_seed_edn_roundtrip.py::test_seed_edn_real_edn` (added in cleanup T2.1)

### REQ-EDN-011 — Ubiquitous

The `verifiers/bermuda/rules/grounded.edn` file shall be valid EDN with
keyword keys, round-tripping through `_io.read_edn_file` to a structure where
every key is a `Keyword`.

**Rationale:** Same as REQ-EDN-010, applied to the grounded-atoms file.
**Tested by:** `verifiers/bermuda/tests/test_rules_seed_edn_roundtrip.py::test_grounded_edn_real_edn` (added in cleanup T2.1)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-cleanup/specs/edn-boundary/
git commit -m "openspec: cleanup delta — edn-boundary REQs"
```

### Task 3.2: Delta — `booklogic-cleanup/specs/bermuda-rules/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-cleanup\specs\bermuda-rules\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: bermuda-rules — change: booklogic-cleanup

## ADD

### REQ-BERMUDA-RULES-001 — State-driven

While the verifier reads `verifiers/bermuda/rules/seed.edn`, the file shall
contain the same semantic content as before the cleanup (sorts, rules, atoms
collections) expressed with `Keyword`-shaped keys.

**Rationale:** Cleanup is a syntax conversion, not a semantic edit.
**Tested by:** `verifiers/bermuda/tests/test_rules_seed_edn_roundtrip.py::test_seed_preserves_semantics` (added in cleanup T2.2)

### REQ-BERMUDA-RULES-002 — State-driven

While the verifier reads `verifiers/bermuda/rules/grounded.edn`, the file
shall contain the same semantic content as before the cleanup expressed with
`Keyword`-shaped keys.

**Rationale:** Same as REQ-BERMUDA-RULES-001 for grounded atoms.
**Tested by:** `verifiers/bermuda/tests/test_rules_seed_edn_roundtrip.py::test_grounded_preserves_semantics` (added in cleanup T2.3)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-cleanup/specs/bermuda-rules/
git commit -m "openspec: cleanup delta — bermuda-rules REQs"
```

### Task 3.3: Delta — `booklogic-cleanup/specs/cljs-orchestrator/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-cleanup\specs\cljs-orchestrator\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: cljs-orchestrator — change: booklogic-cleanup

## ADD

### REQ-CLJS-ORCH-001 — Ubiquitous

The `verifiers/bermuda/cljs-orchestrator/shadow-cljs.edn` configuration shall
declare a `:node-test` build target named `:test` with `:output-to "target/node-test.js"`
and `:ns-regexp "-test$"`, so that `npx shadow-cljs compile test` produces the
file at the path the CI job invokes.

**Rationale:** Without an explicit `:output-to`, the path the CI job runs would
be undefined; the test runner needs both the target declaration and a stable
output path.
**Tested by:** Existence check in `verifiers/bermuda/cljs-orchestrator/shadow-cljs.edn` plus the `cljs-bermuda-test` CI job that runs `npx shadow-cljs compile test && node target/node-test.js` (added in cleanup T3.1)

### REQ-CLJS-ORCH-002 — Ubiquitous

The `bermuda.unify` module shall pass `cljs.test` cases for: identity
unification (a = a → bindings = `[a a]`); and unifying two distinct ground
atoms (no bindings).

**Rationale:** Module currently has zero tests; latent regressions are
silent. The minimum gate is at least one positive + one negative case.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/unify_test.cljs` (added in cleanup T3.2)

### REQ-CLJS-ORCH-003 — Ubiquitous

The `bermuda.ir` module shall pass `cljs.test` cases for malli round-trip of
each of `Atom`, `Formula`, `Claim`, `Verdict`.

**Rationale:** The malli schemas are the public surface; a regression in any
schema breaks contracts across the pipeline.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/ir_test.cljs` (added in cleanup T3.3)

### REQ-CLJS-ORCH-004 — Ubiquitous

The `bermuda.nl-to-fol` module shall pass a `cljs.test` case for `claim->formula`
applied to a quantity-shaped claim (`{:o {:kind :quantity :value 9 :unit "count"}}`)
that produces a `Formula` matching the `ir/Formula` schema.

**Rationale:** Surfaces the latent schema-collision bug the audit flagged
(`~?pred` plus `:variable` shape vs. `:keyword` constraint).
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs::claim->formula-quantity-shape` (added in cleanup T3.4)

### REQ-CLJS-ORCH-005 — Ubiquitous

The `bermuda.phases` module shall pass `cljs.test` cases for: a valid input
passing `translate`; and an invalid input (a `Claim` missing the required
`:source` field) triggering the malli pre-contract violation.

**Rationale:** Pre/post contracts are silent unless an exception is raised.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/phases_test.cljs` (added in cleanup T3.5)

### REQ-CLJS-ORCH-006 — Ubiquitous

The `bermuda.bridge` module shall pass `cljs.test` cases for: `verify-formulas`
invoked with a stub `bermuda-verifier.node` returning a known verdict EDN
string; the returned value is the parsed EDN.

**Rationale:** The bridge does not currently load in the test runner because
the napi addon is not built. A stub permits the test path without building Rust.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/bridge_test.cljs` (added in cleanup T3.6)

### REQ-CLJS-ORCH-007 — Ubiquitous

The `bermuda.core` module shall pass `cljs.test` cases for: `main` dispatching
on each of `"translate"`, `"verify"`, `"typeset"`; and any other arg printing
usage and exiting 2.

**Rationale:** The CLI is the entry point for every CI verification.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/core_test.cljs` (added in cleanup T3.7)

### REQ-CLJS-ORCH-008 — Event-driven

When `claim->formula` receives a `Claim` whose `:p` is a keyword (the
common case), the `Formula` shall not violate the `ir/Formula` malli schema.

**Rationale:** The audit flagged this case as schema-violating today.
Fixing the rule is REQ-CLJS-ORCH-008.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs::claim->formula-keyword-pred` (added in cleanup T4.1)

### REQ-CLJS-ORCH-009 — Ubiquitous

The `.github/workflows/ci.yml` workflow shall include a job named
`cljs-bermuda-test` that on every PR runs `npx shadow-cljs compile test &&
node target/node-test.js` from `verifiers/bermuda/cljs-orchestrator/` (the
path matches the `:output-to` declared in `shadow-cljs.edn` per REQ-CLJS-ORCH-001)
and fails the PR if any test fails.

**Rationale:** Without a CI gate, the new test target is best-effort. CI
makes the gate canonical.
**Tested by:** Workflow run on the PR (added in cleanup T5.1)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-cleanup/specs/cljs-orchestrator/
git commit -m "openspec: cleanup delta — cljs-orchestrator REQs"
```

### Task 3.4: Delta — `booklogic-d2-wiring/specs/ingest-trace/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-d2-wiring\specs\ingest-trace\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: ingest-trace — change: booklogic-d2-wiring

## ADD

### REQ-TRACE-001 — Event-driven

When `verifiers/bermuda/scripts/run_verification.py` is invoked against a
workspace containing `analysis/ingest-trace.edn`, the verifier shall load
its claim atoms from the trace, not from `claims/ledger.jsonl`.

**Rationale:** The trace is the canonical Phase-1 input per mission §D2.
**Tested by:** `verifiers/bermuda/tests/test_run_verification_consumes_trace.py::test_trace_takes_precedence` (added in d2-wiring T1.1, T1.2)

### REQ-TRACE-002 — Event-driven

When `run_verification.py` projects an `ingest-trace.edn` event stream into
the claim shape downstream code expects, only events with head
`claim/verified` (or downstream-aliased `claim/<verified-status>`) shall
contribute claims; `source/ingested` and other heads shall be skipped.

**Rationale:** Only verified claims pass to the Z3 verifier.
**Tested by:** `verifiers/bermuda/tests/test_run_verification_consumes_trace.py::test_only_verified_events` (added in d2-wiring T1.2)

### REQ-TRACE-003 — State-driven

While a workspace contains `claims/ledger.jsonl` and does NOT contain
`analysis/ingest-trace.edn`, `run_verification.py` shall read claims from
the ledger and behave identically to the pre-d2-wiring code path.

**Rationale:** Legacy workspaces must remain operational.
**Tested by:** `verifiers/bermuda/tests/test_run_verification_consumes_trace.py::test_legacy_workspace_still_works` (added in d2-wiring T2.1)

### REQ-TRACE-004 — Event-driven

When the CLJS `bermuda.core` is invoked with subcommand `translate` against
a trace EDN input, the translator shall return a vector of `Formula`s
matching the schema, dispatching on event head.

**Rationale:** D2 wiring spans Python and CLJS. The CLJS side must accept
the trace shape too.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs::translate-trace-input` (added in d2-wiring T4.1)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-d2-wiring/specs/ingest-trace/
git commit -m "openspec: d2-wiring delta — ingest-trace REQs"
```

### Task 3.5: Delta — `booklogic-d2-wiring/specs/cljs-orchestrator/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-d2-wiring\specs\cljs-orchestrator\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: cljs-orchestrator — change: booklogic-d2-wiring

## ADD

### REQ-CLJS-ORCH-010 — Event-driven

When `bermuda.nl-to-fol/event->formula` receives a list whose head is
`source/ingested` or any non-claim head, it shall return `nil` (skip).

**Rationale:** Non-claim events do not produce formulas.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs::event->formula-skips-non-claim` (added in d2-wiring T3.2)

### REQ-CLJS-ORCH-011 — Event-driven

When `bermuda.nl-to-fol/event->formula` receives a list whose head is
`claim/verified`, it shall delegate to `claim->formula` after projecting
the event payload into the legacy `Claim` map shape.

**Rationale:** Re-use existing translation rather than duplicating
business logic.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs::event->formula-verified-delegates` (added in d2-wiring T3.3)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-d2-wiring/specs/cljs-orchestrator/
git commit -m "openspec: d2-wiring delta — cljs-orchestrator REQs"
```

### Task 3.6: Delta — `booklogic-pr4-active-forms/specs/booklogic-dsl/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr4-active-forms\specs\booklogic-dsl\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: booklogic-dsl — change: booklogic-pr4-active-forms

## ADD

### REQ-DSL-010 — Event-driven

When the BookLogic compiler encounters a `defrule` form, it shall expand
the form to a meander rewrite-rule entry appended to the project's
`rules/rules.edn`.

**Rationale:** Active rules-as-data is the v0.2 → v0.4 migration enabler.
**Tested by:** Per-form CLJS test in `booklogic_test.cljs.tmpl::defrule-expansion` (added in pr4 T1.1, T1.2)

### REQ-DSL-020 — Event-driven

When the BookLogic compiler encounters a `defconstraint` form, it shall
emit an intermediate EDN structure carrying `:backend :z3`, `:assert <expr>`,
`:track <tracker>`, and `:on-unsat <ticket>` slots.

**Rationale:** The Rust codegen consumes this intermediate.
**Tested by:** `booklogic_test.cljs.tmpl::defconstraint-intermediate-shape` (added in pr4 T2.1, T2.2)

### REQ-DSL-021 — Event-driven

When the Python codegen receives the intermediate from REQ-DSL-020, it
shall produce Rust source for `rust-verifier/src/axioms.rs` containing one
`assert_and_track` per constraint with the tracker name as the second
argument.

**Rationale:** The Z3 unsat core surfaces tracker names — that's how
defects map back to constraints.
**Tested by:** `skills/neurosym-forge/tests/test_codegen_axioms.py::test_one_constraint_one_assert_and_track` (added in pr4 T2.3, T2.4)

### REQ-DSL-022 — Optional feature

Where a `defconstraint` carries `~=` (approximate-equality), the codegen
shall desugar to `|lhs - rhs| <= tolerance * |rhs|` for relative
tolerance (the default), or `|lhs - rhs| <= tolerance` if
`:tolerance-kind :absolute` is set.

**Rationale:** Mission OQ #1 — `~=` must support the van 't Hoff 3% case
in osmotic-pressure showcase.
**Tested by:** `skills/neurosym-forge/tests/test_codegen_axioms.py::test_approx_equality_relative` and `::test_approx_equality_absolute` (added in pr4 T2.4)

### REQ-DSL-023 — Ubiquitous

Each `defconstraint` shall contribute one row to a generated
`rules/axioms-tracker-map.edn` mapping the tracker name to
`{:constraint-id ... :claim-id ... :source-span ...}` so an unsat core
can be back-resolved to the BookLogic source line.

**Rationale:** Mission OQ #4 — bidirectional traceability.
**Tested by:** `skills/neurosym-forge/tests/test_codegen_axioms.py::test_tracker_map_emitted` (added in pr4 T2.5, T2.6)

### REQ-DSL-030 — Event-driven

When the BookLogic compiler encounters a `defquery` form, it shall emit
an intermediate EDN structure carrying `:backend :cozo`, `:find <vars>`,
`:where <clauses>`, and `:on-result <ticket>` slots.

**Rationale:** Data-path verification (Cozo) is a peer of solver-path
verification (Z3).
**Tested by:** `booklogic_test.cljs.tmpl::defquery-intermediate-shape` (added in pr4 T3.1, T3.2)

### REQ-DSL-031 — Event-driven

When `kg.rs` runs with one or more compiled `defquery` scripts, it shall
invoke Cozo against the workspace knowledge graph and return a vector of
rows for each script.

**Rationale:** Cozo is the active data backend; the stub `kg.rs` is the
v0.4 gap.
**Tested by:** `skills/neurosym-forge/tests/test_kg_cozo_smoke.py::test_one_query_returns_rows` (added in pr4 T3.4)

### REQ-DSL-040 — Event-driven

When the BookLogic compiler encounters a `defremedy` form, it shall emit
an entry into the project's `rules/remedies.edn` carrying `:when <pattern>`,
`:propose <transition>`, and `:requires <human-review|none>`.

**Rationale:** Remedies feed `book-qa.scripts.propose_writeback.py`.
**Tested by:** `booklogic_test.cljs.tmpl::defremedy-emits-remedies-edn` (added in pr4 T4.1, T4.2)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-pr4-active-forms/specs/booklogic-dsl/
git commit -m "openspec: pr4 delta — booklogic-dsl REQs"
```

### Task 3.7: Delta — `booklogic-pr4-active-forms/specs/qa-defect-pipeline/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr4-active-forms\specs\qa-defect-pipeline\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: qa-defect-pipeline — change: booklogic-pr4-active-forms

## ADD

### REQ-QA-PIPE-010 — Event-driven

When `book-qa.scripts.propose_writeback.py` is invoked with a workspace
whose project carries a `rules/remedies.edn`, the writeback pass shall load
the remedies, match the current verdict shape against each remedy's
`:when` pattern, and emit one proposed transition per matched remedy.

**Rationale:** BookLogic remedies are the new auto-proposal source;
`propose_writeback` must know about them.
**Tested by:** `skills/book-qa/tests/test_propose_writeback_booklogic.py::test_remedies_matched` (added in pr4 T4.3, T4.4)

### REQ-QA-PIPE-011 — Event-driven

When a matched remedy emits a proposed transition, the transition entry
in `claims/proposed-transitions.jsonl` shall carry the source remedy's id
in a `:cause-remedy-id` field, in addition to the existing
`:cause-ticket-id` field for verdict-derived remedies.

**Rationale:** Auditability — the writeback log shows which BookLogic
remedy fired which proposal.
**Tested by:** `test_propose_writeback_booklogic.py::test_proposal_carries_cause_remedy_id` (added in pr4 T4.4)

### REQ-QA-PIPE-012 — Unwanted behaviour

If a matched remedy carries `:requires :human-review`, then the proposed
transition shall NOT be auto-applied by `book-qa.scripts.apply_writeback.py`;
the proposal sits in `proposed-transitions.jsonl` until a human invokes
apply manually.

**Rationale:** Sensitive remedies need a human gate.
**Tested by:** `test_propose_writeback_booklogic.py::test_human_review_blocks_auto_apply` (added in pr4 T4.5)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-pr4-active-forms/specs/qa-defect-pipeline/
git commit -m "openspec: pr4 delta — qa-defect-pipeline REQs"
```

### Task 3.8: Delta — `booklogic-pr4-active-forms/specs/verifier-build/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr4-active-forms\specs\verifier-build\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: verifier-build — change: booklogic-pr4-active-forms

## ADD

### REQ-VERIFIER-BUILD-010 — Ubiquitous

The codegen output `rust-verifier/src/axioms.rs` shall be byte-deterministic
given the same `constraints.edn` source: two consecutive `python -m
scripts.codegen_axioms` invocations against the same input must produce
identical bytes.

**Rationale:** Lockstep checking depends on stable codegen.
**Tested by:** `test_codegen_axioms.py::test_codegen_is_deterministic` (added in pr4 T2.4)

### REQ-VERIFIER-BUILD-011 — Ubiquitous

After codegen, `cargo check --manifest-path <project>/rust-verifier/Cargo.toml
--features smt` shall complete with exit 0 against the BookLogic-generated
`axioms.rs` produced by the project template's sample constraints.

**Rationale:** Codegen must produce syntactically and type-valid Rust.
**Tested by:** `skills/neurosym-forge/tests/test_template_cargo_check.py::test_axioms_cargo_check` (added in pr4 T2.7)

### REQ-VERIFIER-BUILD-020 — Ubiquitous

The Rust verifier shall declare `cozo = "0.7"` with `default-features =
false` and `features = ["compact"]` as a non-optional dependency in
`rust-verifier/Cargo.toml.tmpl` (and the Bermuda lockstep `Cargo.toml`).

**Rationale:** Cozo backs the active `kg.rs` query path.
**Tested by:** `skills/neurosym-forge/tests/test_rust_template_shape.py::test_cozo_active_dep` (added in pr4 T3.3)

### REQ-VERIFIER-BUILD-021 — Ubiquitous

`cargo check --manifest-path <project>/rust-verifier/Cargo.toml --features kg`
shall complete with exit 0 against the BookLogic-generated `kg.rs` produced
by the project template's sample queries.

**Rationale:** Same gate as REQ-VERIFIER-BUILD-011, applied to the Cozo
data path.
**Tested by:** `test_template_cargo_check.py::test_kg_cargo_check` (added in pr4 T3.5)

### REQ-VERIFIER-BUILD-022 — Ubiquitous

The `.github/workflows/ci.yml` workflow shall include a job named
`booklogic-template-cargo-check` that runs `cargo check --features smt,kg`
against a scaffolded fresh project on every PR.

**Rationale:** Template-level cargo gate; PR-5 layers the Bermuda-specific
gate on top.
**Tested by:** Workflow run (added in pr4 T3.5)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-pr4-active-forms/specs/verifier-build/
git commit -m "openspec: pr4 delta — verifier-build REQs"
```

### Task 3.9: Delta — `booklogic-pr5-bermuda-migration/specs/bermuda-rules/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr5-bermuda-migration\specs\bermuda-rules\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: bermuda-rules — change: booklogic-pr5-bermuda-migration

## ADD

### REQ-BERMUDA-RULES-010 — Ubiquitous

`verifiers/bermuda/rules/sorts.edn` shall declare the sort registry:
`:entity`, `:claim`, `:source`, `:span`, `:formula`, `:verdict`, plus
primitives.

**Rationale:** Bermuda's BookLogic source needs an explicit sort universe.
**Tested by:** `verifiers/bermuda/tests/test_booklogic_source_shape.py::test_sorts_complete` (added in pr5 T1.1)

### REQ-BERMUDA-RULES-011 — Ubiquitous

`verifiers/bermuda/rules/predicates.edn` shall declare all five existing
predicates (`parishes-count`, `named-islands-count`, `currency-pegged-at-parity`,
`airport-on-island`, `cedar-binomial`) with the typings present in the
pre-migration `prose_patterns.py`.

**Rationale:** Migration must preserve current semantics.
**Tested by:** `test_booklogic_source_shape.py::test_existing_predicates_preserved` (added in pr5 T1.2)

### REQ-BERMUDA-RULES-012 — Ubiquitous

`verifiers/bermuda/rules/predicates.edn` shall additionally declare four new
quantitative predicates: `population` (`:int`), `land-area-km2` (`:real`),
`gdp-usd-billion` (`:real`), `hospital-beds-kemh` (`:int`).

**Rationale:** Mission D4 promises these new claims.
**Tested by:** `test_booklogic_source_shape.py::test_quantitative_predicates_added` (added in pr5 T1.2)

### REQ-BERMUDA-RULES-013 — Ubiquitous

`verifiers/bermuda/rules/lifts.edn` shall contain one `deflift` for every
regex pattern previously hand-coded in `verifiers/bermuda/scripts/prose_patterns.py`,
plus four new lifts for the quantitative predicates.

**Rationale:** Single source of truth for prose-extraction patterns.
**Tested by:** `test_booklogic_source_shape.py::test_lifts_cover_existing_regexes` (added in pr5 T1.3)

### REQ-BERMUDA-RULES-014 — Ubiquitous

`verifiers/bermuda/rules/rules.edn` shall preserve every R-rule's semantics
from any pre-migration `rules/rules.edn` (if such file existed) or remain
empty if no such rules were present pre-migration.

**Rationale:** Migration is semantically faithful.
**Tested by:** `test_booklogic_source_shape.py::test_rules_preserved_or_empty` (added in pr5 T1.4)

### REQ-BERMUDA-RULES-015 — Ubiquitous

`verifiers/bermuda/rules/constraints.edn` shall declare one `defconstraint`
per fact previously asserted by `canonical.rs` (parishes=9, named-islands=181,
currency-peg=true, airport-on-island=:St_Davids_Island, cedar-binomial="Juniperus
bermudiana").

**Rationale:** Constraints replace the hand-coded canonical-fact axioms.
**Tested by:** `test_booklogic_source_shape.py::test_canonical_facts_carried_over` (added in pr5 T1.5)

### REQ-BERMUDA-RULES-016 — Ubiquitous

`verifiers/bermuda/rules/constraints.edn` shall additionally declare
one `defconstraint` per quantitative predicate asserting the canonical
value (e.g. `population` ≈ 64,000) with appropriate tolerance.

**Rationale:** Quantitative predicates need anchor values.
**Tested by:** `test_booklogic_source_shape.py::test_quantitative_constraints_added` (added in pr5 T1.5)

### REQ-BERMUDA-RULES-017 — Ubiquitous

`verifiers/bermuda/rules/queries.edn` shall declare at least one Cozo
`defquery` exercising the data-path verification (e.g. "find every
load-bearing claim with posterior < 0.80").

**Rationale:** Bermuda is the first Cozo consumer in production.
**Tested by:** `test_booklogic_source_shape.py::test_at_least_one_query` (added in pr5 T1.6)

### REQ-BERMUDA-RULES-018 — Ubiquitous

`verifiers/bermuda/rules/remedies.edn` shall declare at least one
`defremedy` (e.g. "if unsat-core surfaces a claim, propose `:refuted`
with `:requires :human-review`").

**Rationale:** First production remedy.
**Tested by:** `test_booklogic_source_shape.py::test_at_least_one_remedy` (added in pr5 T1.7)

### REQ-BERMUDA-RULES-019 — Ubiquitous

`verifiers/bermuda/rust-verifier/src/canonical.rs` shall not exist after
PR-5.

**Rationale:** Codegen makes the hand-coded file obsolete.
**Tested by:** `test_booklogic_source_shape.py::test_canonical_rs_deleted` (added in pr5 T2.3)

### REQ-BERMUDA-RULES-020 — Ubiquitous

`verifiers/bermuda/scripts/prose_patterns.py` shall, after PR-5, contain
no regex patterns; it shall load all patterns from the lift-generated
table at `verifiers/bermuda/rules/.compiled/lift_patterns.py` (or
equivalent path written by the BookLogic compiler).

**Rationale:** Pattern data lives in `lifts.edn`; the Python module is a
thin loader.
**Tested by:** `verifiers/bermuda/tests/test_prose_patterns_is_loader.py::test_no_inline_regexes` (added in pr5 T2.4)

### REQ-BERMUDA-RULES-021 — State-driven

While `examples/bermuda-manual/claims/ledger.jsonl` is current, the ledger
shall contain at least one verified claim per quantitative predicate
(`population`, `land-area-km2`, `gdp-usd-billion`, `hospital-beds-kemh`).

**Rationale:** End-to-end verification requires data to verify.
**Tested by:** `test_booklogic_source_shape.py::test_ledger_carries_quantitative_claims` (added in pr5 T3.1)

## MODIFY

(none — bermuda-rules has only ADD deltas across the v0.4 sprints; the
seed.edn / grounded.edn syntax migration is captured under REQ-EDN-010
and REQ-EDN-011)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-pr5-bermuda-migration/specs/bermuda-rules/
git commit -m "openspec: pr5 delta — bermuda-rules REQs"
```

### Task 3.10: Delta — `booklogic-pr5-bermuda-migration/specs/verifier-build/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr5-bermuda-migration\specs\verifier-build\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: verifier-build — change: booklogic-pr5-bermuda-migration

## ADD

### REQ-VERIFIER-BUILD-030 — Ubiquitous

`verifiers/bermuda/rust-verifier/src/axioms.rs` shall be regeneratable by
invoking the BookLogic compiler against `verifiers/bermuda/rules/`,
producing byte-identical output to the committed file.

**Rationale:** Lockstep check — manual edits to the generated file are
forbidden.
**Tested by:** `verifiers/bermuda/tests/test_axioms_lockstep.py::test_regen_matches_committed` (added in pr5 T2.2)

### REQ-VERIFIER-BUILD-031 — Ubiquitous

`verifiers/bermuda/tests/test_axioms_lockstep.py` shall execute on every
PR and fail loudly if the regenerated `axioms.rs` byte-differs from the
committed file.

**Rationale:** Drift detection.
**Tested by:** `verifiers/bermuda/tests/test_axioms_lockstep.py::test_regen_matches_committed` plus the `.github/workflows/ci.yml` `bermuda-z3-build` job that invokes it (added in pr5 T2.2)

### REQ-VERIFIER-BUILD-040 — Ubiquitous

The `.github/workflows/ci.yml` workflow shall include a job named
`bermuda-z3-build` on `ubuntu-latest` that runs `cargo build
--manifest-path verifiers/bermuda/rust-verifier/Cargo.toml --features z3`
on every PR and fails the PR if the build fails.

**Rationale:** Bundled Z3 build is the canonical CI gate; mission OQ #5.
**Tested by:** Workflow run on the PR (added in pr5 T5.1)

### REQ-VERIFIER-BUILD-041 — Ubiquitous

The `.github/workflows/ci.yml` workflow shall include a job
`bermuda-z3-verify` that, after `bermuda-z3-build` succeeds, runs the
real verifier against `examples/bermuda-manual/` and asserts the verdict
shape is well-formed.

**Rationale:** Build success isn't enough; the verifier must run.
**Tested by:** Workflow run (added in pr5 T5.2)

### REQ-VERIFIER-BUILD-042 — State-driven

While CI is the canonical verifier gate, `verifiers/bermuda/tests/test_run_verification.py`
shall not default to `stub_verifier=True`; tests defaulting to the real
verifier are the new norm. Tests explicitly setting `stub_verifier=True`
remain valid for fast local iteration.

**Rationale:** Stub-by-default masks real verifier regressions.
**Tested by:** `test_run_verification.py::test_default_uses_real_verifier` (added in pr5 T7.1)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-pr5-bermuda-migration/specs/verifier-build/
git commit -m "openspec: pr5 delta — verifier-build REQs"
```

### Task 3.11: Delta — `booklogic-pr5-bermuda-migration/specs/qa-defect-pipeline/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr5-bermuda-migration\specs\qa-defect-pipeline\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: qa-defect-pipeline — change: booklogic-pr5-bermuda-migration

## ADD

### REQ-QA-PIPE-020 — Event-driven

When the Bermuda verifier returns `:unsat` against the v6.0.0 release artifacts
with the ch-02 prose drift at
`examples/bermuda-manual/book/releases/6.0.0/chapter-bundles/ch-02-v6/draft.md:44`,
the verdict's unsat core shall contain the prose-claim id corresponding to
"Richard Norwood divided the colony into eight parishes" plus the ledger
claim id `clm-2026-000008` (parishes=9).

**Rationale:** End-to-end D13 fire on the canonical drift.
**Tested by:** `verifiers/bermuda/tests/test_ch02_drift_e2e.py::test_unsat_core_carries_both_claims` (added in pr5 T6.2)

### REQ-QA-PIPE-021 — Ubiquitous

The book-qa end-to-end smoke suite shall include the ch-02 drift fixture as
one of its scenarios.

**Rationale:** Smoke regression for the headline mission deliverable.
**Tested by:** `verifiers/bermuda/tests/test_ch02_drift_e2e.py::test_drift_fixture_present` (added in pr5 T6.1)

### REQ-QA-PIPE-024 — Ubiquitous

The `.github/workflows/ci.yml` `bermuda-z3-verify` job shall execute the
ch-02 drift fixture on every PR.

**Rationale:** CI must gate the regression on every change.
**Tested by:** `.github/workflows/ci.yml` job `bermuda-z3-verify` step that invokes `pytest verifiers/bermuda/tests/test_ch02_drift_e2e.py` (added in pr5 T6.1)

### REQ-QA-PIPE-022 — Event-driven

When verifier-defects.json carries a `:verdict :unsat` for a build, book-qa
shall emit exactly one D13 ticket per claim id in the unsat core, with
`:severity :critical`.

**Rationale:** Each surfaced claim is one defect.
**Tested by:** `skills/book-qa/tests/test_lint_d13_from_verifier.py::test_unsat_core_to_d13_tickets` (added in pr5 T6.3)

### REQ-QA-PIPE-023 — State-driven

While `examples/bermuda-manual/qa-config.yaml` carries `enable_verification:
true`, the book-qa lint_artifact pass shall read `qa/verification-defects.json`
and incorporate D13 tickets into the defect summary.

**Rationale:** Verification defects are gated by workspace config.
**Tested by:** `test_lint_d13_from_verifier.py::test_config_gate` (added in pr5 T6.3)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-pr5-bermuda-migration/specs/qa-defect-pipeline/
git commit -m "openspec: pr5 delta — qa-defect-pipeline REQs"
```

### Task 3.12: Delta — `booklogic-pr5-bermuda-migration/specs/cljs-orchestrator/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr5-bermuda-migration\specs\cljs-orchestrator\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: cljs-orchestrator — change: booklogic-pr5-bermuda-migration

## ADD

### REQ-CLJS-ORCH-020 — Event-driven

When `bermuda.core` is invoked with the `verify` subcommand against a
workspace containing a built `bermuda-verifier.node` addon, the verifier
shall return a verdict EDN containing `:verdict` (or `:status`) and, on
`:unsat`, a non-empty `:core` vector.

**Rationale:** First real-verifier path in production CLJS.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/core_test.cljs::verify-real-verdict` (added in pr5 T5.2)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-pr5-bermuda-migration/specs/cljs-orchestrator/
git commit -m "openspec: pr5 delta — cljs-orchestrator REQs"
```

### Task 3.13: Delta — `booklogic-pr6-osmotic-showcase/specs/osmotic-pressure-verifier/spec.md`

**Files:**
- Create: `C:\work\russellian-book-suite\openspec\changes\booklogic-pr6-osmotic-showcase\specs\osmotic-pressure-verifier\spec.md`

- [ ] **Step 1: Write the delta.**

```markdown
# Capability delta: osmotic-pressure-verifier — change: booklogic-pr6-osmotic-showcase

## ADD

### REQ-OSMOTIC-001 — Ubiquitous

The `verifiers/osmotic_pressure/` directory shall exist and contain a
project scaffolded by `python -m scripts.scaffold_project --name "Osmotic
pressure" --slug osmotic_pressure`.

**Rationale:** First non-Bermuda verifier.
**Tested by:** `verifiers/osmotic_pressure/tests/test_project_layout.py::test_scaffolded` (added in pr6 T1.1)

### REQ-OSMOTIC-010 — Ubiquitous

`verifiers/osmotic_pressure/rules/sorts.edn` shall declare `:solution`
in addition to the primitives.

**Rationale:** The chemistry domain needs a solution sort.
**Tested by:** `tests/test_booklogic_source_shape.py::test_solution_sort` (added in pr6 T2.1)

### REQ-OSMOTIC-011 — Ubiquitous

`verifiers/osmotic_pressure/rules/predicates.edn` shall declare
`:osmotic-pressure-pa`, `:vant-hoff-i`, `:molarity`, `:temperature-k`,
each typed as `[:solution] :real`.

**Rationale:** Van 't Hoff equation needs these four observables.
**Tested by:** `test_booklogic_source_shape.py::test_four_predicates` (added in pr6 T2.2)

### REQ-OSMOTIC-012 — Ubiquitous

`verifiers/osmotic_pressure/rules/lifts.edn` shall declare at least one
`deflift` for prose extraction in the osmotic-pressure domain.

**Rationale:** Demonstrates lift usage in a non-book domain.
**Tested by:** `test_booklogic_source_shape.py::test_at_least_one_lift` (added in pr6 T2.3)

### REQ-OSMOTIC-013 — Ubiquitous

`verifiers/osmotic_pressure/rules/constraints.edn` shall declare one
`defconstraint` encoding `π ≈ i·M·R·T` (with `R = 8.314`) using `~=`
with `:tolerance 0.03` for relative 3% tolerance.

**Rationale:** Headline showcase constraint; exercises the `~=` operator.
**Tested by:** `test_booklogic_source_shape.py::test_vant_hoff_constraint_with_relative_tolerance` (added in pr6 T2.4)

### REQ-OSMOTIC-020 — Ubiquitous

`verifiers/osmotic_pressure/fixtures/claims_clean.jsonl` shall contain
four verified claims declaring i=2, M=0.154 mol/L, T=298.15 K,
π=780202.5 Pa for a single solution entity.

**Rationale:** Test fixture matching the spec example.
**Tested by:** `verifiers/osmotic_pressure/tests/test_smoke.py::test_clean_sat` (added in pr6 T3.1, T5.1)

### REQ-OSMOTIC-021 — Ubiquitous

`verifiers/osmotic_pressure/fixtures/claims_doctored.jsonl` shall contain
four verified claims identical to the clean fixture except `i=1`.

**Rationale:** Doctored case must trigger unsat.
**Tested by:** `test_smoke.py::test_doctored_unsat` (added in pr6 T3.2, T5.2)

### REQ-OSMOTIC-030 — Event-driven

When the BookLogic compiler is invoked against
`verifiers/osmotic_pressure/`, it shall produce
`verifiers/osmotic_pressure/rust-verifier/src/axioms.rs` containing the
desugared Van 't Hoff `~=` assertion.

**Rationale:** Codegen smoke for the showcase domain.
**Tested by:** `tests/test_codegen.py::test_vant_hoff_axiom_emitted` (added in pr6 T4.1)

### REQ-OSMOTIC-031 — Event-driven

When `cargo build --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml
--features z3,bundled` runs on `ubuntu-latest`, it shall complete with exit 0.

**Rationale:** Cargo build is the canonical CI gate.
**Tested by:** CI job `osmotic-pressure-smoke` (added in pr6 T4.2, T6.1)

### REQ-OSMOTIC-040 — Event-driven

When the osmotic-pressure verifier is invoked against `claims_clean.jsonl`,
the verdict shall be `:sat`.

**Rationale:** Clean-case assertion.
**Tested by:** `test_smoke.py::test_clean_sat` (added in pr6 T5.1)

### REQ-OSMOTIC-041 — Event-driven

When the osmotic-pressure verifier is invoked against `claims_doctored.jsonl`,
the verdict shall be `:unsat`, and the unsat core shall contain the
i=1 claim id.

**Rationale:** Doctored-case assertion; demonstrates traceability.
**Tested by:** `test_smoke.py::test_doctored_unsat` (added in pr6 T5.2)

### REQ-OSMOTIC-050 — Ubiquitous

The `.github/workflows/ci.yml` workflow shall include a job
`osmotic-pressure-smoke` on `ubuntu-latest` that on every PR scaffolds
the project (or uses the committed copy), runs `cargo build`, and exercises
both fixture ledgers, asserting `:sat` and `:unsat` respectively.

**Rationale:** CI gates the showcase claim end-to-end.
**Tested by:** Workflow run (added in pr6 T6.1)

## MODIFY

(none)

## REMOVE

(none)
```

- [ ] **Step 2: Commit.**

```bash
git add openspec/changes/booklogic-pr6-osmotic-showcase/specs/osmotic-pressure-verifier/
git commit -m "openspec: pr6 delta — osmotic-pressure-verifier REQs"
```

---

## Phase 4: GitHub Milestones

Each Milestone is created via `gh api` and tagged on the relevant Tracking Issue
in Phase 5. The Milestone description points readers at the OpenSpec change
directory.

### Task 4.1: Create Milestone `booklogic-cleanup`

**Files:**
- None (GitHub API)
- Note in: `tools/_ears_roadmap_helpers/create_milestones.sh` (scratch, not committed)

- [ ] **Step 1: Verify gh authentication.**

Run: `gh auth status`
Expected: includes `Logged in to github.com account CharlesHoskinson`.

- [ ] **Step 2: Capture the command in the scratch helper.**

Create `tools/_ears_roadmap_helpers/create_milestones.sh`:

```bash
#!/usr/bin/env bash
# Scratch — not committed. Run from repo root.
set -euo pipefail

REPO="CharlesHoskinson/russellian-book-suite"

create_milestone() {
  local title="$1"
  local description="$2"
  gh api "repos/$REPO/milestones" \
    --method POST \
    --field title="$title" \
    --field description="$description" \
    --field state=open
}

create_milestone "booklogic-cleanup" \
  "Sprint 1 of 5. Strip Codex scaffolding; D1 data hygiene on seed.edn/grounded.edn; CLJS test gap closure; nl_to_fol bug fix. See openspec/changes/booklogic-cleanup/proposal.md."

create_milestone "booklogic-d2-wiring" \
  "Sprint 2 of 5. Wire analysis/ingest-trace.edn into the Bermuda verifier; CLJS translate accepts event-stream input. See openspec/changes/booklogic-d2-wiring/proposal.md."

create_milestone "booklogic-pr4-active-forms" \
  "Sprint 3 of 5. Extend BookLogic compiler with defrule, defconstraint, defquery, defremedy; codegen axioms.rs; wire Cozo into kg.rs; book-qa accepts BookLogic remedies. See openspec/changes/booklogic-pr4-active-forms/proposal.md."

create_milestone "booklogic-pr5-bermuda-migration" \
  "Sprint 4 of 5. Migrate Bermuda to BookLogic source; 4 new quantitative predicates; delete canonical.rs; real Z3 CI on ubuntu-latest; ch-02 D13 fires end-to-end. See openspec/changes/booklogic-pr5-bermuda-migration/proposal.md."

create_milestone "booklogic-pr6-osmotic-showcase" \
  "Sprint 5 of 5. Greenfield verifiers/osmotic_pressure/ scaffolded entirely via BookLogic source. Clean + doctored fixture ledgers. Publishes v0.4.0 GitHub Release on merge. See openspec/changes/booklogic-pr6-osmotic-showcase/proposal.md."
```

- [ ] **Step 3: Run the helper.**

Run: `bash tools/_ears_roadmap_helpers/create_milestones.sh`
Expected: five JSON responses each containing `"number": N` (the milestone numbers; capture these for Phase 5 — likely 1, 2, 3, 4, 5 if no prior milestones exist; otherwise next-N).

- [ ] **Step 4: Verify milestones exist.**

Run: `gh api repos/CharlesHoskinson/russellian-book-suite/milestones --jq '.[].title'`
Expected: prints all five new titles.

- [ ] **Step 5: Capture the milestone numbers.**

Write the captured numbers to `tools/_ears_roadmap_helpers/milestone-numbers.txt` (also scratch):

```
booklogic-cleanup                  : <number>
booklogic-d2-wiring                : <number>
booklogic-pr4-active-forms         : <number>
booklogic-pr5-bermuda-migration    : <number>
booklogic-pr6-osmotic-showcase     : <number>
```

This file is consumed by Phase 5 tasks.

- [ ] **Step 6: No commit (scratch helpers are gitignored).**

---

## Phase 5: Tracking Issues

One Tracking Issue per Milestone. Each carries the OpenSpec change directory
link plus the REQ IDs the sprint closes. Closed when the sprint PR merges.

### Task 5.1: Tracking Issue for `booklogic-cleanup`

**Files:**
- None (GitHub API)
- Note in: `tools/_ears_roadmap_helpers/create_tracking_issues.sh` (scratch)

- [ ] **Step 1: Capture the command.**

Append to `tools/_ears_roadmap_helpers/create_tracking_issues.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
REPO="CharlesHoskinson/russellian-book-suite"

# Replace <N> with the milestone number from Phase 4.5
gh issue create \
  --repo "$REPO" \
  --title "[sprint-1] booklogic-cleanup" \
  --milestone "booklogic-cleanup" \
  --label "sprint,openspec" \
  --body "$(cat <<'EOF'
Sprint 1 of 5 in the BookLogic v0.4 finish.

**OpenSpec change:** [`openspec/changes/booklogic-cleanup/`](../tree/main/openspec/changes/booklogic-cleanup)

**Branch:** `feat/booklogic-cleanup`

**Implementation notes:** [`docs/plans/2026-05-17-booklogic-cleanup.md`](../blob/main/docs/plans/2026-05-17-booklogic-cleanup.md)

## REQ IDs closed by this sprint

- REQ-EDN-010, REQ-EDN-011 — seed.edn / grounded.edn round-trip real EDN
- REQ-BERMUDA-RULES-001, REQ-BERMUDA-RULES-002 — data files preserve semantics across migration
- REQ-CLJS-ORCH-001 — shadow-cljs `:test` target
- REQ-CLJS-ORCH-002..007 — module-level cljs.test coverage
- REQ-CLJS-ORCH-008 — `claim->formula` schema-collision fix
- REQ-CLJS-ORCH-009 — `cljs-bermuda-test` CI job

## Done when

- All REQs above are test-covered and passing on `main`
- This issue is closed by the PR merge
EOF
)"
```

- [ ] **Step 2: Run.**

Run: `bash tools/_ears_roadmap_helpers/create_tracking_issues.sh`
Expected: issue created; URL printed.

- [ ] **Step 3: Verify.**

Run: `gh issue list --repo CharlesHoskinson/russellian-book-suite --milestone "booklogic-cleanup" --json number,title`
Expected: one issue with title `[sprint-1] booklogic-cleanup`.

### Task 5.2: Tracking Issue for `booklogic-d2-wiring`

**Files:**
- Note: append to scratch helper

- [ ] **Step 1: Append to scratch helper.**

```bash
gh issue create \
  --repo "$REPO" \
  --title "[sprint-2] booklogic-d2-wiring" \
  --milestone "booklogic-d2-wiring" \
  --label "sprint,openspec" \
  --body "$(cat <<'EOF'
Sprint 2 of 5.

**OpenSpec change:** [`openspec/changes/booklogic-d2-wiring/`](../tree/main/openspec/changes/booklogic-d2-wiring)
**Branch:** `feat/booklogic-d2-wiring`
**Implementation notes:** [`docs/plans/2026-05-17-booklogic-d2-wiring.md`](../blob/main/docs/plans/2026-05-17-booklogic-d2-wiring.md)

## REQ IDs closed

- REQ-TRACE-001..004 — trace consumption + legacy fallback + CLJS translate
- REQ-CLJS-ORCH-010, REQ-CLJS-ORCH-011 — event-aware dispatch

## Done when

- All REQs are test-covered and passing on `main`
- This issue is closed by the PR merge
EOF
)"
```

- [ ] **Step 2: Run the appended `gh issue create` invocation.**

Run: `bash tools/_ears_roadmap_helpers/create_tracking_issues.sh` (executes every appended invocation in the helper; the sprint-1 invocation from Task 5.1 has already run, but `gh issue create` is idempotent only by best effort — if rerun, it creates a duplicate, so comment-out the already-run invocations or run a single fresh invocation manually with the exact command above).

Expected: prints the new issue URL (`https://github.com/CharlesHoskinson/russellian-book-suite/issues/N`).

- [ ] **Step 3: Verify.**

Run: `gh issue list --repo CharlesHoskinson/russellian-book-suite --milestone "booklogic-d2-wiring" --json number,title`
Expected: one issue with title `[sprint-2] booklogic-d2-wiring`.

### Task 5.3: Tracking Issue for `booklogic-pr4-active-forms`

- [ ] **Step 1: Append to scratch helper.**

```bash
gh issue create \
  --repo "$REPO" \
  --title "[sprint-3] booklogic-pr4-active-forms" \
  --milestone "booklogic-pr4-active-forms" \
  --label "sprint,openspec,long-pole" \
  --body "$(cat <<'EOF'
Sprint 3 of 5. **Long pole** — pre-declared a/b split available.

**OpenSpec change:** [`openspec/changes/booklogic-pr4-active-forms/`](../tree/main/openspec/changes/booklogic-pr4-active-forms)
**Branch:** `feat/booklogic-pr4` (or `feat/booklogic-pr4a` + `feat/booklogic-pr4b` if split)
**Implementation notes:** [`docs/plans/2026-05-17-booklogic-pr4.md`](../blob/main/docs/plans/2026-05-17-booklogic-pr4.md)

## REQ IDs closed

- REQ-DSL-010 — defrule expander
- REQ-DSL-020..023 — defconstraint + axioms.rs codegen + ~= operator + tracker map
- REQ-DSL-030, REQ-DSL-031 — defquery + Cozo
- REQ-DSL-040 — defremedy
- REQ-VERIFIER-BUILD-010..011 — codegen determinism + cargo check
- REQ-VERIFIER-BUILD-020..022 — Cozo dep activation + kg cargo check + template CI gate
- REQ-QA-PIPE-010..012 — BookLogic remedy adapter in propose_writeback

## Split criteria (decided after Phase 2 acceptance)

See `design.md` in the OpenSpec change directory.

## Done when

- All REQs are test-covered
- Mission spec § D4 footer updated with merge SHA
- This issue (or both split issues) closed
EOF
)"
```

- [ ] **Step 2: Run the appended invocation.**

Run the same `gh issue create` command manually (or extract it into a one-shot script) — `bash` against the full helper would re-run prior issues. The cleanest approach is to copy the sprint-3 invocation block into a standalone command and execute.

Expected: prints the new issue URL.

- [ ] **Step 3: Verify.**

Run: `gh issue list --repo CharlesHoskinson/russellian-book-suite --milestone "booklogic-pr4-active-forms" --json number,title`
Expected: one issue with title `[sprint-3] booklogic-pr4-active-forms`.

### Task 5.4: Tracking Issue for `booklogic-pr5-bermuda-migration`

- [ ] **Step 1: Append to scratch helper.**

```bash
gh issue create \
  --repo "$REPO" \
  --title "[sprint-4] booklogic-pr5-bermuda-migration" \
  --milestone "booklogic-pr5-bermuda-migration" \
  --label "sprint,openspec" \
  --body "$(cat <<'EOF'
Sprint 4 of 5.

**OpenSpec change:** [`openspec/changes/booklogic-pr5-bermuda-migration/`](../tree/main/openspec/changes/booklogic-pr5-bermuda-migration)
**Branch:** `feat/booklogic-pr5`
**Implementation notes:** [`docs/plans/2026-05-17-booklogic-pr5.md`](../blob/main/docs/plans/2026-05-17-booklogic-pr5.md)

## REQ IDs closed

- REQ-BERMUDA-RULES-010..021 — full BookLogic source + 4 quantitative predicates + canonical.rs deletion + prose-patterns loader + ledger update
- REQ-VERIFIER-BUILD-030..031 — axioms lockstep
- REQ-VERIFIER-BUILD-040..042 — Z3 CI build + verify + stub default drop
- REQ-QA-PIPE-020..023 — D13 fires on ch-02 drift end-to-end
- REQ-CLJS-ORCH-020 — verify subcommand on real verdict

## Done when

- All REQs are test-covered
- `bermuda-z3-build` and `bermuda-z3-verify` CI jobs are green
- Mission spec § D4 footer updated with merge SHA
- This issue closed
EOF
)"
```

- [ ] **Step 2: Run the appended invocation.**

Run the sprint-4 invocation as a standalone command (see Task 5.3 Step 2 for the pattern).

Expected: prints the new issue URL.

- [ ] **Step 3: Verify.**

Run: `gh issue list --repo CharlesHoskinson/russellian-book-suite --milestone "booklogic-pr5-bermuda-migration" --json number,title`
Expected: one issue with title `[sprint-4] booklogic-pr5-bermuda-migration`.

### Task 5.5: Tracking Issue for `booklogic-pr6-osmotic-showcase`

- [ ] **Step 1: Append to scratch helper.**

```bash
gh issue create \
  --repo "$REPO" \
  --title "[sprint-5] booklogic-pr6-osmotic-showcase" \
  --milestone "booklogic-pr6-osmotic-showcase" \
  --label "sprint,openspec,final" \
  --body "$(cat <<'EOF'
Sprint 5 of 5. **Publishes v0.4.0 GitHub Release on merge.**

**OpenSpec change:** [`openspec/changes/booklogic-pr6-osmotic-showcase/`](../tree/main/openspec/changes/booklogic-pr6-osmotic-showcase)
**Branch:** `feat/booklogic-pr6`
**Implementation notes:** [`docs/plans/2026-05-17-booklogic-pr6.md`](../blob/main/docs/plans/2026-05-17-booklogic-pr6.md)

## REQ IDs closed

- REQ-OSMOTIC-001 — scaffold
- REQ-OSMOTIC-010..013 — BookLogic source for the chemistry domain
- REQ-OSMOTIC-020, REQ-OSMOTIC-021 — fixture ledgers
- REQ-OSMOTIC-030, REQ-OSMOTIC-031 — codegen + cargo build
- REQ-OSMOTIC-040, REQ-OSMOTIC-041 — smoke verdicts
- REQ-OSMOTIC-050 — CI job

## Done when

- All REQs are test-covered
- `osmotic-pressure-smoke` CI job is green
- Mission spec § D5 footer updated with merge SHA
- `v0.4.0` GitHub Release published
- This issue closed
EOF
)"
```

- [ ] **Step 2: Run the appended invocation.**

Run the sprint-5 invocation as a standalone command.

Expected: prints the new issue URL.

- [ ] **Step 3: Final cross-sprint verification.**

Run: `gh issue list --repo CharlesHoskinson/russellian-book-suite --label sprint --json number,title`
Expected: five entries (one per sprint, titles `[sprint-1]` through `[sprint-5]`).

---

## Phase 6: Draft v0.4.0 Release

The final Release is created as a draft on sprint 0, published on sprint 5 merge.

### Task 6.1: Create draft v0.4.0 Release

**Files:**
- Note in: `tools/_ears_roadmap_helpers/create_draft_release.sh` (scratch)

- [ ] **Step 1: Capture the command.**

Create `tools/_ears_roadmap_helpers/create_draft_release.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
REPO="CharlesHoskinson/russellian-book-suite"

gh release create v0.4.0 \
  --repo "$REPO" \
  --draft \
  --title "BookLogic v0.4.0" \
  --notes "$(cat <<'EOF'
BookLogic v0.4 — the full DSL landing.

## Highlights

- Real EDN at every Python/CLJS/Rust boundary (PR-1 + sprint 1 D1 cleanup)
- Ingest-trace symbolic event stream consumed by the verifier (PR-2 + sprint 2)
- BookLogic DSL with all seven form families (PR-3 passive + sprint 3 active)
- Bermuda migrated to BookLogic; real Z3 in CI on ubuntu-latest (sprint 4)
- Chemistry-domain osmotic-pressure verifier proving the DSL is reusable (sprint 5)

## Sprints in this release

- [sprint 1: booklogic-cleanup](../../../issues?q=is%3Aissue+milestone%3Abooklogic-cleanup)
- [sprint 2: booklogic-d2-wiring](../../../issues?q=is%3Aissue+milestone%3Abooklogic-d2-wiring)
- [sprint 3: booklogic-pr4-active-forms](../../../issues?q=is%3Aissue+milestone%3Abooklogic-pr4-active-forms)
- [sprint 4: booklogic-pr5-bermuda-migration](../../../issues?q=is%3Aissue+milestone%3Abooklogic-pr5-bermuda-migration)
- [sprint 5: booklogic-pr6-osmotic-showcase](../../../issues?q=is%3Aissue+milestone%3Abooklogic-pr6-osmotic-showcase)

## Documentation

- Mission spec: docs/specs/2026-05-14-booklogic-v0.4-mission-design.md
- Roadmap design: docs/specs/2026-05-17-ears-openspec-roadmap-design.md
- OpenSpec changes: openspec/changes/
- Steady-state capability specs: openspec/specs/

## Acceptance

This release is published after sprint 5 (booklogic-pr6-osmotic-showcase) merges to main with the `osmotic-pressure-smoke` CI job green.
EOF
)"
```

- [ ] **Step 2: Run.**

Run: `bash tools/_ears_roadmap_helpers/create_draft_release.sh`
Expected: returns the draft release URL.

- [ ] **Step 3: Verify.**

Run: `gh release list --repo CharlesHoskinson/russellian-book-suite`
Expected: includes `v0.4.0` with status `Draft`.

---

## Phase 7: GitHub Project board

Projects v2 uses GraphQL. The board is created via `gh api graphql`. UI fallback
is documented if the API path fails.

### Task 7.1: Create Projects v2 board "BookLogic v0.4"

**Files:**
- Note in: `tools/_ears_roadmap_helpers/create_project_board.sh` (scratch)

- [ ] **Step 0: Refresh the `gh` token with the `project` scope.**

The default `gh` token (issued for `repo, gist, read:org, workflow`) cannot call Projects v2 mutations. Add the scope:

Run: `gh auth refresh -s project`
Expected: opens a browser for one-time consent; on return prints `✓ Configured git credential helper for github.com` and `✓ Logged in to github.com as CharlesHoskinson`. Re-run `gh auth status` to confirm `project` is in the scope list.

If the browser cannot open (headless), use `gh auth refresh -s project --hostname github.com --skip-ssh-key` and follow the device-code prompt printed to stdout.

- [ ] **Step 1: Get the owner ID.**

Run: `gh api graphql -f query='query { viewer { id } }' --jq '.data.viewer.id'`
Expected: a node id string like `U_kgDOABCDxyz`. Capture it.

- [ ] **Step 2: Capture the create command in scratch helper.**

Create `tools/_ears_roadmap_helpers/create_project_board.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

OWNER_ID="<from-step-1>"

PROJECT_ID=$(gh api graphql -f query="
mutation {
  createProjectV2(input: {ownerId: \"$OWNER_ID\", title: \"BookLogic v0.4\"}) {
    projectV2 { id number url }
  }
}
" --jq '.data.createProjectV2.projectV2.id')

echo "Project created. ID: $PROJECT_ID"

# Link project to the repo
gh api graphql -f query="
mutation {
  linkProjectV2ToRepository(input: {
    projectId: \"$PROJECT_ID\",
    repositoryId: \"$(gh api repos/CharlesHoskinson/russellian-book-suite --jq '.node_id')\"
  }) {
    repository { name }
  }
}
"
```

- [ ] **Step 3: Run.**

Run: `bash tools/_ears_roadmap_helpers/create_project_board.sh`
Expected: prints `Project created. ID: PVT_kwxxxxx` and the link confirmation.

- [ ] **Step 4: Verify.**

Run: `gh project list --owner CharlesHoskinson --format json | jq '.projects[] | .title'`
Expected: `BookLogic v0.4` appears.

- [ ] **Step 5: If any of the above fails (UI fallback).**

If the GraphQL path returns an error (org-level permissions, deprecated API, etc.):

1. Open https://github.com/users/CharlesHoskinson/projects in a browser.
2. Click "New project" → "Board" → name it "BookLogic v0.4".
3. Settings → Manage access → add the russellian-book-suite repo.
4. Copy the project URL.
5. Record the URL in `AGENTS.md` § OpenSpec workflow (see Phase 9).
6. Skip further GraphQL steps in this phase.

- [ ] **Step 6: Add the five Tracking Issues to the project.**

For each issue created in Phase 5, run:

```bash
gh project item-add <project-number> \
  --owner CharlesHoskinson \
  --url <issue-url>
```

(If using UI fallback, drag-add via the browser.)

- [ ] **Step 7: Add a "Sprint" custom field with the five sprint values.**

Via GraphQL (or UI Settings → Custom fields → Add field "Sprint" → Type "Single select" → values: "1: cleanup", "2: d2-wiring", "3: pr4", "4: pr5", "5: pr6"). Tag each Tracking Issue with its sprint.

---

## Phase 8: Issue + PR templates

### Task 8.1: Issue template for OpenSpec changes

**Files:**
- Create: `C:\work\russellian-book-suite\.github\ISSUE_TEMPLATE\openspec-change.yml`

- [ ] **Step 1: Write the file.**

```yaml
name: OpenSpec change proposal
description: Propose a new OpenSpec change (a sprint, feature, or refactor)
title: "[proposal] <change-slug>"
labels: ["openspec", "proposal"]
body:
  - type: input
    id: change-slug
    attributes:
      label: Change slug
      description: kebab-case identifier; becomes openspec/changes/<slug>/
      placeholder: e.g. booklogic-pr7-foo
    validations:
      required: true

  - type: textarea
    id: why
    attributes:
      label: Why
      description: What problem does this change solve? Cite current state or audit findings.
    validations:
      required: true

  - type: textarea
    id: what
    attributes:
      label: What
      description: Bullet list of the concrete changes.
    validations:
      required: true

  - type: textarea
    id: capabilities
    attributes:
      label: Capabilities touched
      description: |
        List the capabilities (slugs from openspec/README.md) and what kind of delta
        (ADD / MODIFY / REMOVE) the change makes to each.
      placeholder: |
        - edn-boundary: ADD
        - cljs-orchestrator: MODIFY
    validations:
      required: true

  - type: textarea
    id: acceptance
    attributes:
      label: Acceptance
      description: How will you know the change is done?
    validations:
      required: true

  - type: checkboxes
    id: openspec-shape
    attributes:
      label: OpenSpec shape
      description: After this proposal is approved, create the following.
      options:
        - label: openspec/changes/<slug>/proposal.md
        - label: openspec/changes/<slug>/design.md
        - label: openspec/changes/<slug>/tasks.md
        - label: openspec/changes/<slug>/specs/<capability>/spec.md for each touched capability
```

- [ ] **Step 2: Commit.**

```bash
git add .github/ISSUE_TEMPLATE/openspec-change.yml
git commit -m "github: issue template for openspec change proposals"
```

### Task 8.2: PR template extension

**Files:**
- Create or Modify: `C:\work\russellian-book-suite\.github\pull_request_template.md`

- [ ] **Step 1: Check if the template exists.**

Run: `ls -la C:/work/russellian-book-suite/.github/pull_request_template.md 2>&1`

If it exists, the next step modifies; if not, it creates.

- [ ] **Step 2: Write or extend the template.**

```markdown
## Summary

<!-- One paragraph: what this PR changes and why. -->

## OpenSpec change

**Change directory:** `openspec/changes/<change-slug>/`

**REQ IDs closed by this PR:**

<!-- List the REQ IDs implemented or modified, e.g. REQ-EDN-010, REQ-CLJS-ORCH-002. -->

## Test plan

- [ ] All tests cited in REQ IDs (above) pass
- [ ] CI green
- [ ] No regression to merged work

## Commit hygiene

- [ ] No "Co-Authored-By: Claude" / AI attribution
- [ ] Terse, imperative commit messages
- [ ] Each commit references one or more tasks from `openspec/changes/<slug>/tasks.md`
```

- [ ] **Step 3: Commit.**

```bash
git add .github/pull_request_template.md
git commit -m "github: PR template references openspec change"
```

---

## Phase 9: AGENTS.md OpenSpec workflow update

### Task 9.1: Add OpenSpec workflow section to AGENTS.md

**Files:**
- Modify: `C:\work\russellian-book-suite\AGENTS.md`

- [ ] **Step 1: Read the current AGENTS.md to find the insertion point.**

Run: `grep -n "## Known pitfalls\|## Quick orientation reading order" C:/work/russellian-book-suite/AGENTS.md`
Expected: prints two line numbers; insert the new section before "Known pitfalls".

- [ ] **Step 2: Insert the section.**

Add (use the `Edit` tool with the immediately-preceding existing line as anchor; the new content):

```markdown
## OpenSpec workflow

Every change to this repo follows the [OpenSpec convention](https://github.com/Fission-AI/OpenSpec).
See `openspec/README.md` for the directory and REQ-ID conventions.

### Cycle

1. **Propose.** Create `openspec/changes/<change>/proposal.md` (and `design.md`, `tasks.md`,
   `specs/` deltas). Open a draft PR.
2. **Refine.** Iterate until requirements are crisp and spec deltas are agreed.
3. **Execute.** Implement against `tasks.md`. Each test cites the REQ ID(s) it satisfies
   in its docstring or test name (e.g. `def test_REQ_EDN_010_seed_round_trip():`).
4. **Merge.** Squash-merge to `main`. Milestone auto-closes if the PR carries the
   Milestone tag.
5. **Archive.** Move `openspec/changes/<change>/` to `openspec/changes/archive/YYYY-MM-DD-<change>/`.
   Merge the spec deltas into `openspec/specs/<capability>/spec.md`. Publish a GitHub
   Release if the change is a milestone.

### Conventions

- **EARS for requirements.** Five patterns: Ubiquitous, Event-driven, State-driven,
  Optional, Unwanted. See `openspec/README.md` for examples.
- **REQ IDs.** `REQ-<CAPABILITY-SLUG>-<NNN>`. Numbers are stable across PRs.
- **One change = one Milestone = one Tracking Issue = one PR.** (Exceptions: pre-declared
  internal splits like PR-4a / PR-4b.)
- **Implementation notes vs tasks.md.** When a sprint already has an exhaustive TDD plan
  at `docs/plans/`, the OpenSpec `tasks.md` is the lightweight checklist; the plan is
  the source-and-command reference. New sprints (post-v0.4) typically skip the verbose
  plan and let `tasks.md` carry the full content.

### Roadmap visibility

- GitHub Milestones — one per OpenSpec change
- Tracking Issues — one per Milestone, listing the REQ IDs the sprint closes
- Releases — alpha per merged sprint (`v0.4.0-alpha.N`); final release published with the
  last sprint
- GitHub Project "BookLogic v0.4" — Kanban + Timeline view of all sprint issues

```

- [ ] **Step 3: Commit.**

```bash
git add AGENTS.md
git commit -m "agents: document OpenSpec workflow + EARS conventions"
```

---

## Phase 10: Delete orphan + smoke + PR

### Task 10.1: Delete `openspec/changes/codex-phase-0/` (idempotent)

**Files:**
- Delete (if present): `C:\work\russellian-book-suite\openspec\changes\codex-phase-0\`

**Note on merge ordering:** PR #39's sprint-1 plan (`docs/plans/2026-05-17-booklogic-cleanup.md` Task T1.5) also deletes this directory. Whichever PR's execution runs first owns the delete; the second sees a no-op. This task handles both cases.

- [ ] **Step 1: Check whether the directory still exists.**

Run: `test -d C:/work/russellian-book-suite/openspec/changes/codex-phase-0 && echo PRESENT || echo ALREADY-GONE`

- [ ] **Step 2a: If PRESENT, delete and commit.**

```bash
git rm -r C:/work/russellian-book-suite/openspec/changes/codex-phase-0/
git commit -m "openspec: delete orphan codex-phase-0 vestige"
```

Expected: `rm 'openspec/changes/codex-phase-0/PR-33-REVIEW.md'` then commit success.

- [ ] **Step 2b: If ALREADY-GONE, skip with a note.**

No commit. The deletion already landed (either via this branch's earlier iteration or via PR #39's sprint-1 execution that preceded this one). Append a one-line entry to the PR description noting the no-op.

- [ ] **Step 3: Verify.**

Run: `ls C:/work/russellian-book-suite/openspec/changes/codex-phase-0/ 2>&1`
Expected: `No such file or directory`.

### Task 10.2: README.md link to openspec

**Files:**
- Modify: `C:\work\russellian-book-suite\README.md`

- [ ] **Step 1: Find the documentation section.**

Run: `grep -n "## Documentation\|## Repository layout" C:/work/russellian-book-suite/README.md`
Expected: prints line numbers.

- [ ] **Step 2: Add the openspec link.**

In the section listing docs, insert near the top of the documentation block:

```markdown
The repository follows the [OpenSpec convention](https://github.com/Fission-AI/OpenSpec) for change management.
See `openspec/README.md` for the spec-driven workflow and the EARS requirement-ID convention.
```

- [ ] **Step 3: Commit.**

```bash
git add README.md
git commit -m "readme: link to OpenSpec convention"
```

### Task 10.3: Spec-link integrity smoke

**Files:**
- None (read-only check)

**Shell:** Tasks 10.3, 10.4, 10.5 use Bash `for`-loops with `grep` / `find`. On Windows, run inside Git Bash or WSL — they do not work in PowerShell. (PowerShell equivalents are out of scope; the executing session can translate if needed.)

- [ ] **Step 1: List every markdown link to `openspec/` in `docs/specs/2026-05-17-*` and confirm targets exist.**

Run:

```bash
cd C:/work/russellian-book-suite
for f in docs/specs/2026-05-17-*.md docs/plans/2026-05-17-*.md; do
  grep -oE '`?openspec/[a-zA-Z0-9_./-]+`?' "$f" | tr -d '`' | sort -u | while read -r p; do
    [ -e "$p" ] || echo "BROKEN: $f -> $p"
  done
done
```

Expected: no `BROKEN:` lines.

- [ ] **Step 2: List every `docs/plans/2026-05-17-booklogic-*.md` link in each change's `design.md` and confirm.**

Run:

```bash
for f in openspec/changes/booklogic-*/design.md; do
  grep -oE 'docs/plans/2026-05-17-booklogic-[a-zA-Z0-9_-]+\.md' "$f" | sort -u | while read -r p; do
    [ -e "$p" ] || echo "BROKEN: $f -> $p"
  done
done
```

Expected: no `BROKEN:` lines.

### Task 10.4: Capability stub completeness check

**Files:**
- None (read-only check)

- [ ] **Step 1: Confirm 8 stubs.**

Run: `ls openspec/specs/`
Expected: 8 directories listed (alphabetical order).

- [ ] **Step 2: Confirm each carries a spec.md.**

Run:

```bash
for d in openspec/specs/*/; do
  [ -f "$d/spec.md" ] || echo "MISSING: $d/spec.md"
done
```

Expected: no `MISSING:` lines.

### Task 10.5: Spec-delta consistency check

**Files:**
- None (read-only check)

- [ ] **Step 1: Confirm every change directory has the four-file shape (proposal/design/tasks + at least one spec delta).**

Run:

```bash
for d in openspec/changes/booklogic-*/; do
  for f in proposal.md design.md tasks.md; do
    [ -f "$d/$f" ] || echo "MISSING: $d$f"
  done
  [ -d "$d/specs" ] || echo "MISSING-SPECS-DIR: $d"
  [ "$(find "$d/specs" -name 'spec.md' 2>/dev/null | wc -l)" -gt 0 ] || echo "NO-SPEC-DELTAS: $d"
done
```

Expected: no `MISSING:`, `MISSING-SPECS-DIR:`, or `NO-SPEC-DELTAS:` lines.

### Task 10.6: Push + open PR

- [ ] **Step 1: Verify final state.**

Run: `git status -s && git log --oneline ^origin/main HEAD | wc -l`
Expected: empty status; commit count ~20-30 across all phases.

- [ ] **Step 2: Push.**

Run: `git push -u origin feat/ears-openspec-roadmap`

- [ ] **Step 3: Open PR.**

Run:

```bash
gh pr create --title "feat: EARS requirements + OpenSpec changes + GitHub roadmap" --body "$(cat <<'EOF'
## Summary

Sprint 0 of the BookLogic v0.4 finish: lands the requirements + change-management infrastructure before any code change in the remaining sprints.

## OpenSpec change

**Change directory:** `openspec/specs/`, `openspec/changes/booklogic-*/`, `.github/`

**This PR is itself the kickoff change** — it scaffolds the OpenSpec tree it documents. The five subsequent sprint PRs execute against the change directories created here.

## What's here

- `openspec/README.md` + 8 capability spec stubs under `openspec/specs/<capability>/spec.md`
- 5 OpenSpec change directories under `openspec/changes/`, each with `proposal.md`, `design.md`, `tasks.md`, and spec deltas (~13 spec delta files total)
- ~60 EARS requirements distributed across the deltas
- 5 GitHub Milestones (one per sprint)
- 5 GitHub Tracking Issues (one per Milestone)
- Draft `v0.4.0` GitHub Release
- GitHub Project board "BookLogic v0.4" with the five Tracking Issues
- `.github/ISSUE_TEMPLATE/openspec-change.yml` for proposing future changes
- `.github/pull_request_template.md` extended with REQ-ID checklist
- `AGENTS.md` documents the OpenSpec workflow + REQ-ID convention
- Orphan `openspec/changes/codex-phase-0/` deleted

## Test plan

- [x] All 13 spec delta files exist and validate (see Task 10.5 smoke check)
- [x] All 8 capability stubs exist
- [x] No broken markdown links from `docs/specs/2026-05-17-*` or `openspec/changes/*/design.md` to plan or spec files
- [x] All 5 Milestones exist on GitHub
- [x] All 5 Tracking Issues exist with their Milestone tag
- [x] Draft v0.4.0 Release exists
- [x] orphan codex-phase-0 deleted
- [ ] PR CI gates pass

## How to use this PR

Future sprints execute against their OpenSpec change directory, not the legacy TDD plan files (the plan files remain as exhaustive implementation notes). Sprint 1 (PR-cleanup) starts the moment this PR merges.
EOF
)"
```

- [ ] **Step 4: Report PR URL.**

---

## Self-review

Walking the spec § "Scope of this PR (sprint 0)" against this plan:

| Spec clause | Implementing tasks |
|---|---|
| 1. Scaffold 8 capability stubs | 1.1 (openspec/README) + 1.2-1.9 (one task per stub) |
| 2. Scaffold 5 OpenSpec change directories with the four-file shape | 2.1-2.5 (one per sprint) |
| 3. Extract EARS requirements into spec deltas (~125 estimated) | 3.1-3.13 (13 spec delta files; ~60 REQs total — under-counted in the spec, corrected here) |
| 4. `.github/ISSUE_TEMPLATE/openspec-change.yml` | 8.1 |
| 5. Extend `.github/pull_request_template.md` | 8.2 |
| 6. Create 5 GitHub Milestones | 4.1 |
| 7. Create 1 Tracking Issue per Milestone | 5.1-5.5 |
| 8. Create draft `v0.4.0` GitHub Release | 6.1 |
| 9. Create GitHub Project (Projects v2) board | 7.1 |
| 10. Update `AGENTS.md` with OpenSpec workflow | 9.1 |
| 11. Delete `openspec/changes/codex-phase-0/` | 10.1 |

All spec items have implementing tasks.

**Placeholder scan.** No "TBD" / "TODO" / "fill in later". Each delta file contains full EARS REQ text with rationale and `Tested by:` reference. Each `gh api` and `gh issue create` invocation ships verbatim commands. The `<from-step-1>` placeholder in 7.1 step 2 is a deliberate cross-step capture, not a content placeholder.

**Type consistency.** `Keyword`, `read_edn_file`, `write_edn_file`, `Defect`, `assert_and_track`, `defconstraint`, `defquery`, `defremedy`, `defrule` consistent across tasks and deltas. REQ IDs are stable: REQ-EDN-010 appears in cleanup's edn delta and in cleanup's `tasks.md` T2.1 and T2.2; REQ-DSL-020 appears in PR-4's booklogic-dsl delta and PR-4's `tasks.md` T2.1 and T2.2. The "60 REQs" total comes from counting REQ blocks across the 13 delta files (cleanup 11 + d2-wiring 6 + PR-4 14 + PR-5 16 + PR-6 13 = 60, give or take depending on what the executor adds for capability-stub backfill).

**Branch / commit hygiene.** All commits on `feat/ears-openspec-roadmap`. Terse imperative messages. No AI attribution.

**Size:** 10 phases, ~30 tasks. Phases 1, 2, 3 (the openspec scaffolding) are the bulk. Phases 4-7 (GitHub API calls) are mechanical. Phases 8-10 are small.

**Known risks:**

- Projects v2 GraphQL — if it fails, UI fallback documented in Task 7.1 step 5.
- EARS extraction is interpretive; the worked deltas in Phase 3 establish the house style. Future sprints' EARS additions must match.
- The plan documents that ~125 REQs would be the spec's estimate, but the actual extraction surfaces ~60. The difference is real: many TDD-plan acceptance criteria collapse into single ubiquitous REQs. The plan reflects the actual extraction count, not the estimate.
