# EARS + OpenSpec + GitHub roadmap — Design

**Date:** 2026-05-17
**Author:** Charles
**Status:** Draft, pending user approval
**Supersedes:** The freeform-TDD-plan model in `docs/plans/2026-05-17-booklogic-*.md` (those files remain as implementation notes).

## Problem

The five BookLogic Claude-only finish plans (PR #39) are freeform markdown TDD checklists. Three structural deficiencies surface as the v0.4 mission moves into execution:

1. **No requirements layer.** Each plan ships test code and acceptance criteria intermixed. A reader cannot answer "what must the system do?" without reading 1,000-3,000 lines of test scaffolding. Tracing a test back to a behavioural requirement is manual.
2. **No project-level visibility.** GitHub has no Milestones, no Releases, no Project board. The work is invisible outside the repo. There is no canonical place where a stakeholder reads "where are we in the v0.4 mission?".
3. **OpenSpec convention partially adopted.** `openspec/changes/codex-phase-0/` exists but holds only a PR review (not the canonical four-file shape). The repo claims OpenSpec discipline without practising it.

## Goal

Land all three layers in one PR, before sprint 1 (PR-cleanup) begins:

- EARS-shaped requirements per capability under `openspec/specs/<capability>/spec.md`
- OpenSpec changes (`proposal.md`, `design.md`, `tasks.md`, `specs/` deltas) under `openspec/changes/<sprint>/` for each of the five remaining sprints
- GitHub Milestones, tracking Issues, and a draft `v0.4.0` Release that mirror the OpenSpec changes

## Non-goals

- No rewrite of the merged PR-1/2/3 implementation work.
- No deletion of the existing TDD plan files — they become implementation notes linked from each sprint's OpenSpec `design.md`.
- No per-task Issue creation for the small sprints (cleanup, D2-wiring, PR-6); only PR-4 and PR-5 justify per-task Issues.

## Approach

### Sprint sequence

```
sprint 0  PR-ears-openspec      ← THIS PR
sprint 1  PR-cleanup            → executes openspec/changes/booklogic-cleanup/
sprint 2  PR-d2-wiring          → executes openspec/changes/booklogic-d2-wiring/
sprint 3  PR-4                  → executes openspec/changes/booklogic-pr4-active-forms/
sprint 4  PR-5                  → executes openspec/changes/booklogic-pr5-bermuda-migration/
sprint 5  PR-6                  → executes openspec/changes/booklogic-pr6-osmotic-showcase/
                                  → publish v0.4.0 Release
```

### Capability decomposition

Capabilities are the durable surfaces; sprints are deltas. Eight capabilities:

| Capability | Owner | Affected sprints |
|---|---|---|
| `edn-boundary` | neurosym-forge | cleanup (data hygiene), PR-5 (artifact lockstep) |
| `ingest-trace` | book-knowledge + bermuda verifier | D2-wiring |
| `booklogic-dsl` | neurosym-forge template | PR-4 |
| `bermuda-rules` | verifiers/bermuda | cleanup, PR-5 |
| `cljs-orchestrator` | verifiers/bermuda | cleanup (tests), D2-wiring (dispatch), PR-5 (verify subcmd) |
| `qa-defect-pipeline` | book-qa | PR-4 (writeback adapter), PR-5 (D13 fire) |
| `verifier-build` | rust-verifier + CI | PR-4 (codegen check), PR-5 (real Z3) |
| `osmotic-pressure-verifier` | new | PR-6 |

Each capability gets `openspec/specs/<capability>/spec.md` (the steady-state truth) and each sprint's `openspec/changes/<sprint>/specs/<capability>/spec.md` carries that sprint's delta.

### EARS conventions

Five EARS patterns with stable IDs `REQ-<CAPABILITY-SLUG>-<NNN>`:

```markdown
### REQ-EDN-001 — Ubiquitous

The neurosym-forge package shall expose `read_edn` and `write_edn` callables
that together round-trip the EDN subset documented at §D1.

### REQ-EDN-002 — Event-driven

When `write_edn` receives a `Keyword` instance, the writer shall emit
`:name` or `:namespace/name` without surrounding quotes.

### REQ-EDN-003 — Unwanted behaviour

If `read_edn` encounters a tagged literal (`#inst`, `#uuid`) or a set
literal (`#{...}`), the reader shall raise `EdnReadError` with the
byte offset.

### REQ-EDN-004 — State-driven

While the workspace contains both `claims/ledger.jsonl` and
`analysis/ingest-trace.edn`, the verifier shall prefer the trace.

### REQ-EDN-005 — Optional

Where the workspace declares `enable_verification: true` in
`qa-config.yaml`, the verifier shall write `verification-defects.json`
into `qa/`.
```

Conventions:
- One numbered REQ per behaviour. Numbers are stable across PRs.
- Tests cite the REQ ID in their docstring or test name (`def test_edn_001_round_trip(): ...`).
- `tasks.md` checkbox entries cite the REQ IDs they satisfy.
- A spec delta file at `openspec/changes/<sprint>/specs/<capability>/spec.md` lists ADD/MODIFY/REMOVE per REQ. The steady-state file at `openspec/specs/<capability>/spec.md` is the union of all merged deltas.

### OpenSpec change file shape

Per sprint:

```
openspec/changes/booklogic-cleanup/
├── proposal.md            # WHY + WHAT; doubles as GitHub Milestone body (~100 lines)
├── design.md              # technical approach (~200 lines)
├── tasks.md               # checklist; each task cites REQ IDs (~400 lines)
└── specs/
    ├── bermuda-rules/spec.md
    ├── cljs-orchestrator/spec.md
    └── edn-boundary/spec.md
```

The five existing TDD plans (`docs/plans/2026-05-17-booklogic-{cleanup,d2-wiring,pr4,pr5,pr6}.md`) stay at their current paths and are referenced from each OpenSpec change's `design.md` as "implementation notes — exhaustive command/code reference complementary to tasks.md."

### GitHub roadmap

- **Milestones** — five, named `booklogic-cleanup`, `booklogic-d2-wiring`, `booklogic-pr4-active-forms`, `booklogic-pr5-bermuda-migration`, `booklogic-pr6-osmotic-showcase`. Description includes a link to `openspec/changes/<sprint>/proposal.md`.
- **Tracking Issues** — one per Milestone, titled `[sprint-N] <sprint-name>`, body lists the REQ IDs the sprint closes plus the OpenSpec change path. Closed when the PR merges.
- **Per-task Issues** — only for PR-4 and PR-5 (task counts justify the issue overhead). Cleanup, D2-wiring, PR-6 use checklist-in-tracking-issue.
- **Releases** — alpha per merged sprint (`v0.4.0-alpha.1` for cleanup … `v0.4.0-alpha.5` for PR-6). Final `v0.4.0` published after PR-6 merges, with combined release notes.
- **GitHub Project (Projects v2)** — board named "BookLogic v0.4", two views: Timeline (showing Milestone targets) and Kanban (Backlog / In Progress / In Review / Done).
- **Issue + PR templates** — `.github/ISSUE_TEMPLATE/openspec-change.yml` for proposing new changes; `.github/pull_request_template.md` extension that asks for the OpenSpec change path and the REQ IDs the PR closes.

### Scope of this PR (sprint 0)

1. Scaffold `openspec/specs/` with 8 capability `spec.md` stubs (steady-state, mostly empty — populated as changes land via the merge-delta rule).
2. Scaffold 5 `openspec/changes/<sprint>/` directories from the existing TDD plans, each with `proposal.md`, `design.md`, `tasks.md`, and per-capability `specs/` deltas.
3. Extract EARS requirements from each TDD plan into the appropriate spec delta file (estimated ~25 REQs per sprint, ~125 total across v0.4).
4. Add `.github/ISSUE_TEMPLATE/openspec-change.yml`.
5. Extend `.github/pull_request_template.md` (create if absent).
6. Create 5 GitHub Milestones via `gh api`.
7. Create 1 tracking Issue per Milestone.
8. Create draft `v0.4.0` GitHub Release with the roadmap as its body.
9. Create a GitHub Project (Projects v2) board.
10. Update `AGENTS.md` with the OpenSpec workflow (proposal → tasks → archive) and the EARS REQ-ID convention.
11. Delete the orphan `openspec/changes/codex-phase-0/` (sweeping ahead of PR-cleanup).

### Steady-state workflow after sprint 0

Every future change to the repo follows the OpenSpec cycle:

1. **Propose.** Create `openspec/changes/<change>/proposal.md` (and optionally `design.md`, `tasks.md`, `specs/` deltas). Open a draft PR.
2. **Refine.** Iterate on the proposal until requirements are crisp and the spec deltas are agreed.
3. **Execute.** Implement against `tasks.md`. Tests cite REQ IDs. Each commit references one or more tasks.
4. **Merge.** Squash-merge to main. GitHub Milestone auto-closes if the PR has the Milestone tag.
5. **Archive.** Move `openspec/changes/<change>/` to `openspec/changes/archive/YYYY-MM-DD-<change>/`. Merge the spec deltas into the steady-state `openspec/specs/<capability>/spec.md`. Publish a GitHub Release if the change is a milestone.

The TDD plans become a legacy artifact format. New work uses OpenSpec from proposal forward.

## Risks

- **GitHub Projects v2 API** is GraphQL-only and rate-limited. The Project board creation is a one-shot; if it fails, fall back to manually creating it via the GitHub UI and noting the URL in `AGENTS.md`.
- **Projects v2 OAuth scope.** The default `gh` token issued for `repo, gist, read:org, workflow` cannot call `createProjectV2` or `linkProjectV2ToRepository` — Projects v2 mutations require the `project` scope. The plan's Phase 7 begins with `gh auth refresh -s project`; if a future executor skips it, the GraphQL call returns a 403 and the UI fallback kicks in. Not silent; not blocking.
- **EARS extraction is interpretive.** Different readers can write different REQ wordings for the same TDD step. The first sprint (cleanup) sets the house style; subsequent sprints' EARS extraction must match.
- **Tracking-Issue staleness.** If a Tracking Issue isn't updated as tasks complete, it diverges from `tasks.md`. Convention: `tasks.md` is the source of truth; the Tracking Issue is generated from it at PR-open time and updated only at significant milestones.
- **Spec-delta merge into steady-state.** When a sprint merges, its `specs/<capability>/spec.md` delta must be merged into the top-level `openspec/specs/<capability>/spec.md`. This is a manual step in the archive flow. Risk: forgetting it leaves the steady-state file stale.

## Open questions

1. **One sprint = one OpenSpec change?** Yes. Sprint and change are 1:1 in this v0.4 mission. Multi-change sprints are possible in future missions but not this one.
2. **EARS REQ IDs sequential across capabilities or per-capability?** Per-capability. `REQ-EDN-001` is independent of `REQ-CLJS-ORCH-001`. Keeps numbering stable when capabilities evolve independently.
3. **Should TDD plans be deleted after sprint 0?** No. They stay as detailed implementation notes. Future sprints (post-v0.4) may not produce them at all — `tasks.md` plus `design.md` suffices for most work.
4. **GitHub Project board: classic or v2?** Projects v2 — supports timeline view, custom fields, and is the GitHub-recommended path. Worth the API friction.
5. **Per-PR EARS-coverage CI gate?** Future enhancement. v0.4.0 ships without it; v0.4.x may add a CI job that greps tests for REQ IDs and fails the PR if a new REQ is unreferenced.

6. **OpenSpec slash-command interface (`/opsx:propose`, `/opsx:apply`, `/opsx:archive`)?** Deferred. The canonical OpenSpec CLI is a Node-based tool; this PR adopts the directory + spec-delta convention without the CLI. The workflow in `AGENTS.md § OpenSpec workflow` describes the manual `git` + `gh` equivalents. Adopting the CLI is a separate, scoped change post-v0.4.0 (would add a Node tool dep and a `.opsx/` config dir). Tracked as a follow-up; not blocking the convention adoption.

## Deliverables

1. This design doc (committed in sprint 0 PR).
2. One implementation plan at `docs/plans/2026-05-17-ears-openspec-migration.md`.
3. Sprint 0 PR landing the openspec/ tree, GitHub Milestones, Tracking Issues, draft Release, Project board, and AGENTS.md updates.
4. After sprint 0 merges: each subsequent sprint executes against its OpenSpec change and closes its Milestone.

## Acceptance for sprint 0

- `openspec/specs/` contains 8 capability stubs
- `openspec/changes/` contains 5 sprint directories with the four-file shape
- ~125 EARS requirements distributed across the spec delta files
- 5 GitHub Milestones exist
- 5 Tracking Issues exist (one per Milestone)
- Draft `v0.4.0` Release exists
- `openspec/changes/codex-phase-0/` deleted
- `AGENTS.md` documents the OpenSpec workflow + REQ-ID convention
- No regression to existing CI gates
