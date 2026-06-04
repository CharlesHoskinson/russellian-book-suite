# CI redesign — sequenced fix plan

**Date:** 2026-05-29. From the multi-persona CI audit (`docs/audits/2026-05-29-ci-system-audit/`). Order: P0 (make main green) -> P1 (security/correctness hardening) -> P2 (cost/DX/reproducibility). CI changes are high-blast-radius and validated against **real CI runs** (push branch, observe).

## P0 (3 items)

### `P0-ruff-fix` — Delete the two ruff offenders that hold main red
- **Change:** In tools/readme-lint/tests/test_lint_readme.py delete line 81 (the duplicate `from scripts.lint_readme import parse_single_section`; symbol already imported at line 7). In tools/russellian-style-audit/scripts/health_check.py delete line 215 (`any_warn = True`) and line 208 (`any_warn = False` initialiser) — `any_warn` is never read; status is decided by all_pass/any_fail at lines 228-233.
- **Files:** tools/readme-lint/tests/test_lint_readme.py, tools/russellian-style-audit/scripts/health_check.py
- **Validation:** From repo root: `nix develop -c ruff check .` exits 0 (or `python -m ruff check .` with the CI-pinned ruff). Then push and observe the `nix preflight` job and `ci required ✓` go green on the resulting ci.yml run.

### `P0-second-red-surface` — Triage the second red surface on the in-flight HEAD run
- **Change:** Run 26657565786 (HEAD 8247af2) is additionally red on `python-skill (book-compose / ubuntu-24.04)` and `python-skill (neurosym-forge / macos-latest)` pytest legs — independent of the ruff failure. Pull the failing logs, identify root cause (test regression vs env), and fix so the matrix is green. P0-ruff-fix alone will NOT make main green if these pytest legs stay red.
- **Files:** skills/book-compose/tests/**, skills/neurosym-forge/tests/** (TBD by log)
- **Validation:** `gh run view 26657565786 --log-failed`; reproduce the failing leg locally with `cd skills/book-compose && .venv/Scripts/python.exe -m pytest tests/ -q` (and neurosym-forge). After fix, both legs green on a fresh ci.yml run.

### `P0-merge-group-trigger` — Add merge_group trigger so the merge queue can report ci required ✓
- **Change:** ci.yml `on:` has only `push` (main) and `pull_request`; the ruleset enables a merge_queue whose required check is `ci required ✓`. With no `merge_group:` trigger, ci.yml never runs in the queue, the required check never reports, and the queue wedges. Add `merge_group:` to ci.yml `on:`. Must land before/with any approval-count change (P1-approvals) so the first queued merge does not stall.
- **Files:** .github/workflows/ci.yml (on: block, lines 2-5)
- **Validation:** After merge, enqueue a trivial PR into the merge queue and confirm ci.yml fires a `merge_group` run and `ci required ✓` reports green to the queue (GitHub PR/queue UI). actionlint the file first.

## P1 (8 items)

### `P1-hoist-lint-always-run` — Split lint into its own always-run job (closes the pure-Python-PR hole)
- **Change:** Create a `lint` job in ci.yml with no `needs` and no rust gate, running ruff + clj-kondo + nixpkgs-fmt + cargo-fmt on every PR/push (plain runner, or fast nix). Remove the lint target from preflight's path OR keep Makefile lint but invoke it from the new job. This makes ruff/clj-kondo run at PR time on pure-Python PRs (the root cause of red-since-PR-122). Depends on P0-ruff-fix (so the new always-run job is green when introduced).
- **Files:** .github/workflows/ci.yml, Makefile (lint target), lefthook.yml (add pre-push whole-tree `nix develop -c ruff check .`)
- **Validation:** Open a pure-Python test PR that introduces a deliberate ruff error; confirm the new `lint` job runs and fails it at PR time (today it would skip). Revert the deliberate error; lint goes green.

### `P1-wire-invariant-linters` — Actually execute the NFR-4/NFR-5 invariant linters in the gate
- **Change:** ci/lint_no_direct_http.py, ci/lint_no_shadow_writes.py and ci/test_*.py are never run by any gate (grep of Makefile/.github finds no `pytest ci`, `ci.lint`). Add `python -m pytest ci/ -q` and `python -m ci.lint_no_direct_http` to the new always-run lint job (and mirror in lefthook pre-commit). Add `ci/**` to the paths-filter so changes to the linters are themselves gated. (ci/.import-linter stays documentation-only; real enforcement is the AST scanner.)
- **Files:** .github/workflows/ci.yml (lint job + paths-filter), lefthook.yml, Makefile
- **Validation:** Run `python -m pytest ci/ -q` and `python -m ci.lint_no_direct_http` locally — both pass. Open a PR adding `import requests` to a skill and confirm the lint job fails it.

### `P1-aggregator-fail-closed` — Make ci required ✓ fail-closed on skipped always-run jobs
- **Change:** Replace `contains(needs.*.result,'failure')`/`'cancelled'` with explicit per-need checks: assert `needs.lint.result == 'success'` and `needs.python-skill-matrix.result == 'success'`; for change-scoped `preflight`/`cargo-test` accept `success` OR `skipped` but never `failure`/`cancelled`. A skipped always-run job is now a failure. Also widen the paths-filter to include `skills/**`, `tools/**`, `**/*.py`, `**/*.clj*`, `**/*.edn`, `**/*.nix` so skill/tooling changes trigger preflight. Stage behind P1-hoist-lint (so lint can never be legitimately skipped). High blast radius — verify the ruleset shows the check satisfied before relying on it.
- **Files:** .github/workflows/ci.yml (required job lines 236-253, changes filter lines 36-46)
- **Validation:** Force a skipped always-run job in a scratch branch and confirm `ci required ✓` now goes red (not green). Confirm a normal green PR still passes. Watch a real run before enabling as required.

### `P1-ascii-required-name` — Rename the required check to ASCII and add a drift assertion
- **Change:** Rename `ci required ✓` (U+2713) to `ci-required` in ci.yml:237, scripts/ruleset-apply.sh:41, and docs/operations/branch-protection.md:11 — all in ONE commit. Add a step in the always-run lint job that greps the aggregator job name from ci.yml and diffs it against the ruleset JSON context, failing on mismatch. Removes the non-ASCII byte-match foot-gun. High blast radius: a mismatched rename wedges every merge — re-apply the ruleset and confirm the check shows satisfied before merging anything else.
- **Files:** .github/workflows/ci.yml, scripts/ruleset-apply.sh, docs/operations/branch-protection.md
- **Validation:** Run `bash scripts/ruleset-apply.sh` (or dry-run the gh api), then `gh api repos/CharlesHoskinson/russellian-book-suite/rulesets/<id>` and confirm the required context is `ci-required` and a green run satisfies it.

### `P1-drop-unused-pr-write` — Drop unused pull-requests:write from ci.yml (runs untrusted fork code)
- **Change:** ci.yml top-level permissions grant `pull-requests: write` (line 9) with a comment referencing the ci-budget job — but ci-budget is a SEPARATE workflow with its own permissions. No ci.yml job calls the PR API. Set ci.yml permissions to `contents: read` only. ci-budget.yml keeps its own write grant. Verify no ci.yml step calls `gh pr`/`gh api` first.
- **Files:** .github/workflows/ci.yml (permissions block lines 7-9)
- **Validation:** Grep ci.yml for `gh pr`/`gh api`/PR-comment usage — none. After change, a normal PR run still completes green (no permission error).

### `P1-ruleset-approvals` — Require 1 approval + last-push-approval; scope Dependabot auto-merge
- **Change:** In scripts/ruleset-apply.sh set `required_approving_review_count: 1` and `require_last_push_approval: true`. Add a narrow auto-merge policy (separate workflow or Dependabot config) that auto-approves/merges ONLY patch-level dependency bumps, so routine bumps stay unattended while substantive PRs require a human. Update docs/operations/branch-protection.md in the same change. Depends on P0-merge-group-trigger (queue must work first) and P1-aggregator (gate must be honest first). Medium blast radius: too-strict could stall the queue with no reviewer — coordinate with repo owner.
- **Files:** scripts/ruleset-apply.sh, docs/operations/branch-protection.md, .github/dependabot.yml or a new auto-merge workflow
- **Validation:** Re-apply ruleset; open a non-Dependabot PR and confirm merge is blocked until 1 approval. Confirm a patch Dependabot PR still auto-merges once green.

### `P1-job-timeouts` — Add timeout-minutes to every job in every workflow
- **Change:** Set per-job timeout-minutes at ~2x observed p99: ~20-25 preflight, ~15 python-skill/cargo legs, ~10 changes/ci-divergence-summary/required, ~30 nightly full-Windows matrix. No job currently sets one (default 360min); a hung nix/brew/npm/pip step can peg a runner for 6h and block the queue (cancel-in-progress=false on main).
- **Files:** .github/workflows/ci.yml, ci-budget.yml, ci-legacy.yml, nightly-flake-drift.yml, onboarding-bench.yml
- **Validation:** actionlint passes on all five files; confirm a normal run completes well under the set limits (no spurious timeout).

### `P1-pin-runner-images-toolchain` — Pin floating runner images and the Rust toolchain channel
- **Change:** Replace `macos-latest`→`macos-15` (ci.yml:62,171) and ci-legacy `ubuntu-latest`→`ubuntu-24.04` throughout. Pin dtolnay/rust-toolchain to `toolchain: 1.90.0` to match flake.nix:39 (ci.yml:181 and ci-legacy:300,332,417). For brew z3, pin a formula version or install z3 via the nixpkgs pin so the SMT layer is identical across jobs. Stops silent OS/Xcode/brew/SMT drift defeating the SHA-pinning effort.
- **Files:** .github/workflows/ci.yml, .github/workflows/ci-legacy.yml
- **Validation:** actionlint passes; cargo-test legs report the pinned rustc (`rustc --version` == 1.90.0) and a known z3 version; runs reproduce green.

## P2 (6 items)

### `P2-network-retries` — Add retry/backoff and caching to single-shot network steps
- **Change:** Wrap spaCy wheel download (ci.yml:115-120), apt-get (177), brew (180), npm ci, and nix-installer/cache steps in retry (nick-fields/retry or shell `for i in 1 2 3; do ... && break; sleep $((i*5)); done`). Cache the spaCy wheel via actions/cache keyed on the model version so it is not re-fetched every run. Reduces flaky reds on the required check.
- **Files:** .github/workflows/ci.yml, .github/workflows/ci-legacy.yml
- **Validation:** Re-run a leg; confirm the spaCy wheel is cache-restored on the second run and that a simulated transient failure retries rather than reddening.

### `P2-pip-lockfiles` — Commit per-skill constraints/lockfiles and pin pip
- **Change:** Generate per-skill constraints.txt (pip-compile/uv), install with `pip install -e <skill> -c constraints.txt` (or --require-hashes), pin pip itself, and key the pip cache on the lockfile (setup-book-python:22-28 currently keys on pyproject.toml). Wire Dependabot to bump the lockfiles. Land skill-by-skill behind CI — a bad lock breaks one leg, not all 24. Largest effort; does not block green.
- **Files:** .github/actions/setup-book-python/action.yml, skills/*/constraints.txt (new), .github/dependabot.yml
- **Validation:** For one piloted skill, two CI runs of the same commit install byte-identical transitive versions; cache key changes only when the lock changes.

### `P2-matrix-coverage-gaps` — Add missing skills and verifiers to the test matrices
- **Change:** Add scrapling-fetch (highest supply-chain risk per dependabot.yml) and syntopical-metabook to python-skill-matrix (ci.yml:63-71) — at least a Linux install+import smoke leg — and to the nightly windows-full list. Add adsc-clinical and epidemiology to cargo-test (ci.yml:171-172) and corresponding Makefile smoke targets, or document the exclusion in docs/operations/ci-platforms.md. Closes the gap where Dependabot bumps the highest-risk skill with zero CI signal.
- **Files:** .github/workflows/ci.yml, .github/workflows/nightly-flake-drift.yml, Makefile, docs/operations/ci-platforms.md
- **Validation:** New legs appear and pass on a PR run; a deliberate import error in scrapling-fetch is now caught.

### `P2-actionlint-and-legacy` — Run actionlint on PRs and resolve ci-legacy's dead-coverage state
- **Change:** Move actionlint into an always-run ci.yml job (paths-filter .github/**) feeding the aggregator, so workflow-YAML errors are caught pre-merge (today actionlint only runs when ci-legacy edits itself). Then decide ci-legacy: fold its unique coverage (py3.11/3.12 matrix, z3/cljs/end-to-end smokes) into a scheduled nightly that actually runs, or delete the 470-line file. Current self-trigger-only state is maintenance cost with near-zero signal.
- **Files:** .github/workflows/ci.yml, .github/workflows/ci-legacy.yml, .github/workflows/nightly-flake-drift.yml
- **Validation:** A PR with a malformed ci.yml expression is now caught by actionlint at PR time; the py3.11/3.12 matrix runs on a schedule (or ci-legacy is removed and no longer accrues SHA-pin churn).

### `P2-nightly-alerting-and-drift` — Add failure alerting to scheduled jobs and deepen the flake-drift check
- **Change:** Add `issues: write` + an on-failure open/update-tracking-issue step to nightly-flake-drift.yml and onboarding-bench.yml so red scheduled runs are actionable (today they fail silently). Make checks.flake-drift recurse into verifier submake `ci` targets (compare against `make -pn` or expand them) instead of the one-level `make -n`, or delete the shadow scripts/ci-steps.txt and assert the Makefile against ci.yml directly.
- **Files:** .github/workflows/nightly-flake-drift.yml, .github/workflows/onboarding-bench.yml, flake.nix (checks.flake-drift), scripts/ci-steps.txt
- **Validation:** Force a nightly failure on a scratch run and confirm a tracking issue is opened; introduce drift inside a verifier `ci` target and confirm flake-drift now catches it.

### `P2-ci-budget-and-onboarding-value` — Fix or retire ci-budget and onboarding-bench so they assert something real
- **Change:** ci-budget gates on updatedAt-createdAt (queue-inclusive turnaround, not runner-minutes), is opt-in by a label no one applies, and computes over last-20 GREEN runs (likely empty given main was red for weeks). Either switch to per-job started_at/completed_at (billable timing API) before gating, or make it advisory-only and run it scheduled with a trend issue. onboarding-bench runs a stub backend with no pinned deps and no failure gate — install neurosym-forge[dev] for reproducibility and assert report structure, or drop it.
- **Files:** .github/workflows/ci-budget.yml, .github/workflows/onboarding-bench.yml
- **Validation:** ci-budget reports a wall-time/cost number derived from real timing data (or is clearly advisory); onboarding-bench fails on an empty/garbage report and installs pinned deps.
