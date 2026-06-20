# CI follow-up audit — 2026-06-16

Live audit of CI on `origin/main` @ `c695de9`, run after the 2026-06-16
comprehensive audit (`../2026-06-16-comprehensive-audit/`) and its remediation
plan. Scope: verify the comprehensive audit's CI verdicts against the **live
GitHub repo state** (not just the workflow YAML), re-check the 2026-05-29 plan's
17 items, and surface anything new.

The comprehensive audit's `findings-cicd.md` graded the CI design as largely
fixed and well-architected. That holds at the **YAML/scripts** layer. This
follow-up adds one thing that file did not check: the **live GitHub
configuration**. That is where the one genuinely critical finding lives.

## Headline: `main` is unprotected — the gate is a dead letter

`findings-cicd.md` records branch-protection as *"FIXED + guarded"* on the basis
that `scripts/ruleset-apply.sh:40` and `docs/operations/branch-protection.md`
require exactly the `ci-required` context the workflow emits, and
`scripts/check-required-name.sh` guards against drift. All true — **of the
scripts**. But the ruleset was never applied to the repository:

- `gh api repos/CharlesHoskinson/russellian-book-suite/rulesets` → `[]`
- `gh api .../branches/main/protection` → `404 Branch not protected`
- `branches/main.protected` → `false`
- The `merge_group` event has **never fired** across the last 60+ runs (only
  `pull_request`, `push`, `schedule`, `workflow_dispatch`).

Consequences already observed on `main`:

- Red Dependabot bumps landed directly (`27586462264`, `27586465843` — lint-job
  failures from format violations in the bump).
- A flaky `neurosym-forge` z3 test reddened a push run (`27594754776`) on the
  same commit that passed green on its PR run.

Every one of the 17 prior hardening items and every CI fix in the comprehensive
audit is only as effective as this one switch. **It is the highest-leverage
action in either audit.**

**Fix:** an admin runs `bash scripts/ruleset-apply.sh`, then verifies:

```
gh api repos/CharlesHoskinson/russellian-book-suite/rulesets        # expect non-empty, active
gh api repos/CharlesHoskinson/russellian-book-suite/rules/branches/main  # expect context ci-required
```

Then enqueue one trivial PR to confirm `merge_group` actually fires and
`ci-required` reports to the queue before relying on it.

## Status of the 2026-05-29 plan's 17 items

13 held, 1 held-with-improvement, 2 partial-by-design, **1 effectively
regressed**.

| # | Item | Status |
|---|------|--------|
| P0-1 | ruff-fix | Held — `ruff-check` is a flake check (`nix/treefmt.nix`) |
| P0-2 | second red surface (pytest legs) | Held; a *different* neurosym z3 test now flakes (see P0-B) |
| P0-3 | merge_group trigger | In YAML (`ci.yml:6`), **inert live** — no queue configured |
| P1-1 | hoist lint always-run | Held, re-implemented as `nix flake check -L` (`ci.yml:36-59`) |
| P1-2 | wire invariant linters | Held — `invariant-lint` flake check runs `ci.lint_no_direct_http`, `check_windows_canary`, `pytest ci/` |
| P1-3 | aggregator fail-closed | Held; python-skill-matrix moved to change-scoped (dynamic matrix) |
| P1-4 | ASCII required name + drift assert | Held — `required-name` flake check asserts ci.yml job == ruleset context |
| P1-5 | drop unused pull-requests:write | Held — `ci.yml` top-level `contents: read` |
| P1-6 | ruleset approvals + Dependabot auto-merge | **Regressed in effect** — script sets 1-approval + last-push, but ruleset not applied; no auto-merge workflow exists |
| P1-7 | job timeouts everywhere | Held — every job in all workflows |
| P1-8 | pin runner images + toolchain | Held/improved — z3+rustc now sourced from the Nix flake shell |
| P2-1 | network retries + caching | Held — backoff on actionlint/npm; models cached via `setup-models` |
| P2-2 | pip lockfiles | Partial by design — `book-qa/constraints.txt` pilot; pip pinned 25.2 |
| P2-3 | matrix coverage gaps | Held/exceeded — all 4 verifiers in cargo + cljs; scrapling-fetch, metabook added |
| P2-4 | actionlint on PRs + retire ci-legacy | Held — `ci-legacy.yml` deleted; coverage folded into `nightly.yml` |
| P2-5 | nightly alerting + drift | Held — `alert-on-failure` jobs; single-source matrix replaces shadow `ci-steps.txt` |
| P2-6 | ci-budget + onboarding value | Held (advisory) |

## New findings

### P0

- **P0-A — `main` unprotected / ruleset unapplied.** See headline. One command, admin-gated.
- **P0-B — flaky `neurosym-forge` z3 test reds `main`.**
  `skills/neurosym-forge/tests/test_smt_fit.py:186` asserts `eps is None` but z3 on
  macos-15 nondeterministically returns `2.874669e-14` instead of `unknown`
  (`27594754776` red; identical commit green on its PR run). A flaky **required**
  check will wedge the merge queue once P0-A lands. Fix: tolerate an effectively-zero
  epsilon (`eps is None or abs(eps) < 1e-9`) or pin a deterministic z3 config
  (fixed `random_seed`, disable model completion) for this case.

### P1

- **P1-A — Dependabot patch auto-merge promised but absent.** No auto-merge
  workflow, no `dependabot.yml` auto-merge block, repo `allow_auto_merge: false`.
  After P0-A, weekly grouped bumps pile up behind the new approval rule. Add a
  narrow auto-merge keyed on `dependabot[bot]` + `version-update:semver-patch`.
- **P1-B — `python-skill-matrix` fail-open on a no-selection PR.** Reasonable for
  docs-only diffs, but the safety now rests entirely on `compute_matrix.py`'s
  shared-path list. Add `ci/test_compute_matrix.py` asserting every
  `skills/<name>/**` path maps to that skill's selection.
- **P1-C — Clojure (`deps.edn`) deps have zero CVE scanning.** Dependabot has no
  Clojure ecosystem (documented at `dependabot.yml:92-95`); the 4 verifiers' cljs
  paths are real code. Add a scheduled `clj-watson`/`clj-holmes` advisory job.
  (Already queued as remediation T5.6.)

### P2

- **P2-A — `ci/**` is in the *rust* paths-filter (`ci.yml:130`).** Editing CI
  linters triggers 4 cargo + 4 cljs verifier jobs that `ci/**` cannot affect. Drop
  it; lint/compute-matrix already gate `ci/**`.
- **P2-B — openspec `tier4-cross-os-ci-matrix` is largely obsolete.** Its premise
  (Linux-only matrix) is stale: python-skill matrix runs `[ubuntu-24.04, macos-15,
  windows-2022]`, cargo runs Linux+macOS, nightly adds `aarch64-linux`. Archive or
  retarget to its only unrealized slice (Windows cargo via WSL). Keep its 3 concrete
  bug hypotheses (regex Unicode escapes, path-separator fallthrough, CRLF golden
  hash) as test tasks.
- **P2-C — ci-budget targets are aspirational.** Targets p50 ≤120s / p99 ≤240s vs
  observed green runs of 5-9 min. Advisory-only so harmless, but it will always
  report "over budget". Recalibrate to observed reality or measure billable per-job
  minutes.

## What is genuinely solid (no work needed)

SHA-pinning (100% across all 5 workflows), per-job timeouts (100%),
Nix-flake-sourced z3+rustc (best-in-class reproducibility — one pinned solver
links everywhere), single-source skill matrix feeding both PR and nightly
(eliminates the drift class), retired `ci-legacy`, scoped `issues:write`,
documented `ci:none` exclusions for the two non-package skills, and complete,
intentional coverage of the 16 skills + 4 verifiers.

## Recommended CI increment (prioritized)

1. **Apply the ruleset (P0-A).** Verify `merge_group` fires.
2. **Fix the flaky neurosym z3 test (P0-B)** so a protected `main` does not wedge.
3. **Dependabot patch auto-merge + `allow_auto_merge` (P1-A).**
4. **compute_matrix path-coverage test (P1-B)** + **Clojure CVE scan (P1-C / T5.6).**
5. **Cleanup:** drop `ci/**` from rust filter (P2-A); archive/retarget tier4 (P2-B);
   recalibrate ci-budget (P2-C).

P0-A and P0-B are the CI-hotfix track folded into Sprint 2; the rest map onto
remediation Sprint 5's CI track.
