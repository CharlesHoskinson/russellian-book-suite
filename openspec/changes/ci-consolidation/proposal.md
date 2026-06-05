# Proposal: ci-consolidation

## Why

Three problems, observed directly on `main` (2026-06-04):

1. **Main is intermittently red.** The last three `ci` failures on `main`
   (runs 26973979791, 26985818903, 26986518016) share one root cause: the
   `warm HF model cache` step in the `neurosym-forge` matrix legs downloads
   `sentence-transformers/all-MiniLM-L6-v2` from HuggingFace on a cache miss,
   HF 429-rate-limits GitHub's shared runner IPs, and the 5/10/15s backoff
   does not outlast HF's rate-limit window. Worse: `actions/cache` only saves
   in its post-job step *when the job succeeds*, so a cold cache plus a 429
   means the cache is never populated and every subsequent run on that OS
   reds again — a death spiral (currently live on the Windows leg).

2. **Every `skills/**` PR pays for the full 38-leg matrix.** A one-line
   change to one skill runs 12 skills × 3 OSes. macOS legs dominate queue
   time and runner cost. The skill list itself is registered in four places
   that must be kept in sync by hand: the `matrix.skill` axis in `ci.yml`,
   the `include:` overrides in `ci.yml`, a duplicate of both in
   `nightly-flake-drift.yml`, and the hand-rolled YAML parser in
   `ci/check_windows_canary.py`. Forgetting to register a new skill has
   happened three times (feynman-style, halmos, iacr-review all landed with
   zero CI signal until later commits).

3. **Dead weight and copy-paste.** `ci-legacy.yml` (460 lines) duplicates
   ~90% of current coverage and only triggers when it edits itself; its
   retirement (started in commit 5ac707e) was never finished. The
   `symlink siblings` JS block is duplicated verbatim between `ci.yml` and
   `nightly-flake-drift.yml`; the bash `retry()` helper is pasted 3+ times;
   spaCy/HF model setup is inlined into the matrix job. `ci-budget.yml`
   spawns 4–6 skipped phantom runs per PR push. The guard test
   `verifiers/bermuda/tests/test_axioms_lockstep.py::test_ci_yaml_has_bermuda_z3_jobs`
   asserts jobs that no longer exist in `ci.yml` and is dodged with a
   `--deselect`.

## What

1. **Green:** split the HF/spaCy model caches into explicit
   `actions/cache/restore` + warm + `actions/cache/save` steps so a warmed
   model is persisted even when a later step fails, and lengthen the warm
   backoff to exponential 15/30/60/120s.

2. **Faster:** introduce `.github/ci/skills-matrix.json` as the single
   source of truth for the python-skill matrix, plus a `compute-matrix` job
   that scopes PR-time legs to the skills the PR actually touches.
   Push-to-main and merge_group always run the full matrix, so nothing
   lands unverified. A registration lint makes "forgot to add the new
   skill" a lint failure instead of silent zero coverage.

3. **Modular / maintainable:** extract `symlink-siblings` and
   `setup-models` composite actions consumed by both `ci.yml` and the
   nightly; delete `ci-legacy.yml` with an explicit coverage disposition
   (py3.11/3.12 legs, bermuda example-pipeline smoke, and the cljs test
   move to the nightly; advisory-only jobs are dropped; the rest is already
   covered); fix the stale bermuda lockstep guard; narrow `ci-budget.yml`
   triggers to `[labeled]` + dispatch.

## Spec impact

- MODIFY `REQ-CI-040` (matrix source of truth moves to `skills-matrix.json`)
- ADD `REQ-CI-045` (skill registration invariant)
- ADD `REQ-CI-046` (PR-time matrix scoping; full matrix on main/merge_group)
- ADD `REQ-CI-047` (model-cache save-on-warm-success; bounded backoff)
- ADD `REQ-CI-048` (ci-budget trigger hygiene)

See `specs/ci-platform/spec.md` in this change for the deltas.

## Non-goals

- No change to the Makefile preflight chain or `scripts/ci-steps.txt`
  (the flake-drift contract is untouched).
- No change to the `ci-required` ruleset context or
  `scripts/check-required-name.sh`.
- No re-enabling of sccache; no merge-queue adoption; no HF_TOKEN secret
  (cache hardening was chosen over authenticated HF access).
