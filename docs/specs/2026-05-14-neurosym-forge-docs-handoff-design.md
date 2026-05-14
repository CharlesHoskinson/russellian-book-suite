# neurosym-forge documentation handoff — Design

Date: 2026-05-14
Author: Charles
Status: Draft, pending user approval

## Problem

`neurosym-forge` v0.3 is on main but lacks operator-facing documentation. The repo README shows a one-line table entry and a one-paragraph "Verifiers (optional)" section. The skill's `references/` directory has five technical reference files (atomspace-edn, grounded-atoms, metta-idioms, phase-boundaries, rewrite-rule-style) but no top-level walkthrough. There is no operator runbook, no concepts overview, and no end-to-end recipe.

This work writes the missing docs. The actual writing happens in a separate Claude session driven by a brief in the repo. This spec defines what that brief contains and what the pasteable prompt that points at it looks like.

## What ships

Two artifacts produced in this branch:

1. **`docs/handoffs/2026-05-14-neurosym-forge-documentation-brief.md`** — the comprehensive work order. Lives in git as a record. The next session reads this and executes against it.
2. **`docs/handoffs/2026-05-14-neurosym-forge-documentation-prompt.md`** — the pasteable handoff text. ~400-500 characters. The user opens a fresh Claude Code session in the repo, pastes this, and the session reads the brief and proceeds.

A new `docs/handoffs/` directory is established as the convention for cross-session work orders. A README at `docs/handoffs/README.md` documents the convention.

## Brief contents

The brief is the next session's primary input. Sections:

### Mission
One paragraph stating the goal: produce four documentation artifacts that make `neurosym-forge` operator-ready. Audience: ML/AI engineers who want to scaffold their own verifier projects.

### Context

- What `neurosym-forge` is, in 2-3 sentences
- Current version (v0.3, merged at SHA `10b1a2b`)
- Where the skill lives (`skills/neurosym-forge/`)
- Pointer to existing docs (the five `references/*.md` files and the worked example)
- Recent PRs (#14, #18, #21) that shaped the current state

### Sources to read before writing

Explicit list:
- `skills/neurosym-forge/SKILL.md`
- `skills/neurosym-forge/references/*.md` (all five)
- `skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md`
- `docs/specs/2026-05-13-neurosym-forge-design.md` (v0.1 design)
- `docs/specs/2026-05-14-neurosym-forge-v0.3-mission-design.md` (v0.3 umbrella)
- `verifiers/bermuda/README.md`
- `docs/operations/2026-05-12-bundle-c-runbook.md` (style and length pattern to follow)
- `README.md` § "The seven core skills (plus one optional)" and § "Verifiers (optional)"

### Deliverables

Four artifacts, with target paths and required sections for each:

1. **`docs/operations/neurosym-forge-runbook.md`** (NEW)
   - Recipe-based, ~250-400 lines, patterned on `docs/operations/2026-05-12-bundle-c-runbook.md`
   - Sections: prerequisites; scaffold a project; ingest a ledger; extract prose; add a sort/rule/grounded atom; wire D13 into book-qa; run end-to-end against Bermuda (stubbed + real); troubleshoot common failures
   - Every command is copy-pasteable; every expected output is shown

2. **`docs/concepts/neurosym-forge.md`** (NEW directory + file)
   - Conceptual overview, ~150-300 lines
   - Sections: the EDN-as-Atomspace IR; the four atom kinds; the MeTTa idiom mapping (`=`, `:`, `!`, `match`, `superpose`/`collapse`, grounded atoms, self-reflection); the axioms hook contract (v0.3); composition with `book-qa` via D13
   - Cross-links to the skill's `references/*.md` for depth

3. **README expansion** — `README.md` only
   - Replace the existing one-paragraph "Verifiers (optional)" section with a longer subsection
   - Covers what scaffolding produces, the axioms hook, the typical workflow, links to the runbook and concepts doc
   - Keep concise; the deep prose belongs in the dedicated docs (no duplication)

4. **`skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md`** (EXPAND existing)
   - Fuller end-to-end walkthrough with real commands and expected outputs
   - Reference implementation for what a non-Bermuda verifier looks like
   - Length doubles roughly (currently ~50 lines; target ~100-150)

### Style authority

The session uses the existing repo skill family for prose discipline:

- `russellian-style` linters: every new prose file passes zero critical findings (hedges, modifier budget, parallel structure, rhythm, listicle abstraction, signal density)
- `humanizer` skill's AI-fingerprint catalog: no em-dash overuse, no rule-of-three, no "essentially"/"fundamentally"/"key insight", no numbered proof steps, no excessive bold
- Repo conventions: terse human commits, no AI attribution, no Co-Authored-By, one problem per commit

### Workflow for the session

The session uses the same superpowers stack we have been using:

1. Read the brief end-to-end
2. Invoke `superpowers:brainstorming` to confirm scope with the user (or proceed if user has already confirmed)
3. Invoke `superpowers:writing-plans` to produce a TDD-shaped plan. The plan has no Python tests, but each prose artifact gets a lint-pass checkpoint
4. Invoke `superpowers:subagent-driven-development` to execute, with one subagent per deliverable
5. Open a single PR titled `docs: full neurosym-forge documentation`

### Acceptance criteria

- All four deliverables produced
- Russellian-style linters report zero critical findings on each new prose file (run via `cd skills/russellian-style && .venv/Scripts/python.exe -m scripts.<linter>` for each)
- Humanizer pass produces no critical findings
- Commits follow repo conventions
- PR opens cleanly; CI green (the existing lint-workflow + book-qa + book-thesis test jobs should not regress)

### Out of scope

- New skill features
- Changes to existing skills' SKILL.md beyond cross-linking
- Rewriting `skills/neurosym-forge/references/*.md` (those are reference detail; the new concepts doc summarises and links)
- Anything from PR-2 or PR-3 of the v0.3 mission
- Touching `verifiers/bermuda/` content beyond linking

## Prompt contents

The prompt file is shorter and pasteable. Structure:

```
You are working in the russellian-book-suite repo at
C:\Users\charl\code\russellian-book-suite. Read the brief at
docs/handoffs/2026-05-14-neurosym-forge-documentation-brief.md
and execute it.

The brief is self-contained. It tells you the mission, the source
materials, the four deliverables, the style authority (russellian-style
+ humanizer), and the workflow (brainstorm → plan → subagent execution).

Begin by reading the brief, then invoke superpowers:brainstorming to
confirm scope with me. Use git worktrees for parallel agent edits.
```

The prompt deliberately defers all detail to the brief — keeps the paste short and means the brief is the single source of truth.

## `docs/handoffs/` convention

New directory at repo root. The README in it:

```
# docs/handoffs/

Cross-session work orders. Each handoff is a pair of files:

- `<date>-<topic>-brief.md` — the comprehensive work order. Lives in
  git as the contract between sessions.
- `<date>-<topic>-prompt.md` — the pasteable text the operator drops
  into a fresh Claude session to kick off the work.

A handoff is the right tool when work needs to span sessions and the
context of one session is not portable to the next. The brief replaces
that context by stating the mission, sources, deliverables, and
acceptance criteria explicitly.

Briefs persist in git after the work is done. They are useful as
templates for similar future handoffs.
```

## Workspace mutation

This branch touches:

- New: `docs/handoffs/README.md`
- New: `docs/handoffs/2026-05-14-neurosym-forge-documentation-brief.md`
- New: `docs/handoffs/2026-05-14-neurosym-forge-documentation-prompt.md`
- New (this file): `docs/specs/2026-05-14-neurosym-forge-docs-handoff-design.md`

Nothing else. No code, no existing docs modified. The next session does the actual doc work in a separate branch.

## Non-goals

- Writing the documentation itself in this branch (that is the next session's job)
- Modifying any skill source code
- Touching the existing skill references
- Creating a `docs/concepts/` directory (that comes from the next session's PR)

## Estimated effort

~1 hour for this branch (write brief, write prompt, write handoffs README, commit, open PR). The actual documentation work the brief unlocks is roughly 1-2 days for the next session.
