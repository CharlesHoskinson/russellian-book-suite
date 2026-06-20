# HFR v2 PR Reconciliation & Landing — Design

**Status:** Approved design (2026-06-20). Goal: get the HFR v2 feature branch
`hfr-v2-liveliness` (PR [#262](https://github.com/CharlesHoskinson/russellian-book-suite/pull/262))
reconciled with current `main` and merged, as **one** PR, with the full CI matrix green.

## Divergence (the facts)

- **Merge-base:** `52632ec` (2026-06-18).
- **Branch ahead of main:** 61 commits — the HFR v2 feature (Plans 1–5: `liveliness-signals`
  profiler + 8 scorers, `russellian-style` v2 floor ruleset, `triadic-voice-v2`, and the new
  `voice-eval` 20×20 harness).
- **Main ahead of branch:** 15 commits to absorb — the design-intelligence-KG / liveliness
  thread (incl. `42a99d0 Scaffold liveliness-signals skill`, dependabot + CI-matrix
  registration for it) plus the 2 bermuda axioms re-bake commits (`0952562`, `0d10513`).
- **Only 2 real merge conflicts**, both `add/add` in `skills/liveliness-signals/`, both where
  the **branch is a strict superset** of main's scaffold:
  - `pyproject.toml` — branch only adds `click>=8`/`typer>=0.9` to the `ci`/`dev` extras.
  - `skill_api.py` — branch = main's stub **+** `load_profile`/`score_passage`/`SIGNAL_NAMES`.
- **Clean (no conflict):** `skills-matrix.json` auto-merges to the correct **union**
  (`liveliness-signals` from main + `voice-eval` from branch — the branch never registered
  `liveliness-signals`, so no duplication); `dependabot.yml`/`ci.yml` are touched by main
  only; the ~28 design-KG files + the bermuda re-bake come in as clean adds.

## Approach: merge `main` → branch

Chosen because the conflict surface is tiny and the feature history is worth keeping.
Rejected: **rebase** (replays 61 commits; the liveliness conflicts resurface repeatedly —
high risk) and **squash-reset** (discards the 5-plan history). One merge commit makes #262
conflict-free.

## Components

1. **Pre-merge: land the 2 unpushed bermuda commits on `origin/main` first.** Local `main`
   is 2 ahead of `origin/main` (the bermuda re-bake). Pushing those to `origin/main` first
   keeps #262 purely HFR v2 (otherwise the bermuda fix rides into the feature PR). Requires
   explicit go-ahead to push `main`; gated in the plan.
2. **Merge + conflict resolution.** `git merge origin/main`; resolve the 2 conflicts by
   taking the branch's superset versions (verified supersets — no content lost); commit.
3. **Merge-correctness checks (structural, not tests).** Confirm: design-KG files present;
   bermuda re-bake present; `skills-matrix.json` is the union with no dup; `dependabot.yml`/
   `ci.yml` carry main's liveliness registration; no `liveliness-signals` file regressed to
   the scaffold; the merge result equals the union of both sides (no accidental deletions).
4. **Verification matrix.**
   - **Local (feasible):** `voice-eval` (30 tests), `triadic-voice-v2` (stdlib), and
     `russellian-style` + `liveliness-signals` when the spaCy `en_core_web_sm` model installs.
   - **CI is the authoritative comprehensive gate:** the heavier suites main brought
     (`book-knowledge` design-KG, `book-compose`/`halmos`/`book-qa` live-* tests, Cozo,
     verifiers) run in the PR's python-skill matrix + nix preflight + cargo-test. **CI must be
     green on #262 before merge.**
5. **Landing.** After CI green: merge #262 into `main` (a **merge commit**, preserving the
   5-plan history, per repo norm). Then reconcile local `main` (fast-forward to the merged
   `origin/main`), delete the local feature branch, and confirm the remote branch state.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Auto-merged `skills-matrix.json` semantically wrong (dup/malformed) | Structural check #3 + `python -c "import json; json.load(...)"` validation |
| spaCy model unavailable locally → can't run liveliness/russellian suites | Treat CI as the gate; local run is best-effort, not a blocker |
| design-KG suites (main) break under the merged tree | CI python-skill matrix + the design-KG deterministic-contract job catch it before merge |
| bermuda fix mixed into the feature PR | Push bermuda to `origin/main` first (component 1) |
| Conflict resolution silently drops a scaffold-only addition | Both conflicts verified as branch-supersets; check #3 re-confirms post-merge |

## Out of scope

The actual **20×20 run** (generate + judge in-session, record deltas/win-rate/drift) is a
later activity — this work lands the *harness*, not the run. No decomposition into multiple
PRs (the user chose to land #262 as one).
