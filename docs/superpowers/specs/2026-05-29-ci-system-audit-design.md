# CI-system audit & redesign — design

**Date:** 2026-05-29
**Status:** Approved (brainstorm)
**Scope:** The entire CI system — all five GitHub Actions workflows (`ci.yml`, `ci-budget.yml`, `ci-legacy.yml`, `nightly-flake-drift.yml`, `onboarding-bench.yml`), the `setup-book-python` composite action, `dependabot.yml`, the `ci/` invariant linters, the branch-protection ruleset (`scripts/ruleset-apply.sh` + `docs/operations/branch-protection.md`), the lefthook pre-commit gate, and the Makefile / Nix `preflight` chain.

## Goal

Audit the CI system through four independent persona lenses, synthesize the findings into one coherent target design + strategy, and implement a sequenced fix that gets `main` green and then hardens the system. Appetite: **full redesign + harden**.

Grounding fact at kickoff: `main` is red because the `nix preflight (lint + bake + regression + verifiers)` job fails at `Makefile:15` (`make lint`) with "Found 2 errors" (clj-kondo is clean; the errors come from another linter in the chained `lint` target), which cascades into `ci required ✓`.

## Personas

1. **Release/Build Engineer** — gate correctness, job dependency graph, required-checks alignment with live job names, fail-closed aggregation, matrix coverage, what can pass vacuously.
2. **SRE / Reliability** — flakiness, retries, cache key correctness/hit-rate, concurrency & cancellation, timeouts, the nightly flake-drift mechanism, runner pinning.
3. **Security / Supply-chain** — Action SHA-pinning, `GITHUB_TOKEN` permissions (least privilege), secret handling, `pull_request_target`/pwn-request exposure, OIDC, artifact provenance.
4. **Cost / DX / Reproducibility** — runner-minute & matrix cost, feedback latency, Nix/WSL local-vs-CI drift, lefthook↔CI parity, workflow DRY/maintainability, the budget job.

## Pipeline (the swarm)

- **Phase 0 — Recon (grounding):** one agent establishes ground truth — inventories every CI file, extracts the exact failing linter behind `make lint`, captures the real job graph and recent run outcomes, and notes which CI files the recent remediation already changed. Output: a recon brief shared with every persona.
- **Phase 1 — Persona review (parallel):** four persona agents, each reviewing the whole CI surface + the recon brief, emit structured findings and redesign proposals: `{id, persona, title, severity, blast_radius, effort, file, problem, recommendation}`.
- **Phase 2 — Adversarial verify:** each material finding/proposal is checked by an independent skeptic against the real configs and run logs. CI changes are high-blast-radius; bad proposals must die before the plan. Survivors carry a verdict + evidence.
- **Phase 3 — Synthesis (CI architect):** one agent reconciles the four personas into a single target CI design + strategy, explicitly resolving cross-persona tensions (cost vs coverage, speed vs reproducibility, security vs convenience), and emits a prioritized, sequenced fix plan: **P0 make `main` green** (the `make lint` failure and any other red) → **P1 security/correctness hardening** → **P2 cost/DX/reproducibility**.

## Implementation (after the swarm)

Execute the synthesized plan with a fix→QA loop (the pattern proven in the audit remediation): implementer per change-group, independent QA agent, retry on FAIL. Validate against **real CI** by pushing the branch and observing runs (the `workflow` OAuth scope is now granted, so workflow-file pushes succeed). Order: P0 to green, then P1, then P2, re-running CI after each tranche.

## Deliverables

- A committable multi-persona CI audit + synthesized strategy / target-design document under `docs/audits/`.
- A sequenced fix plan under `docs/superpowers/plans/`.
- The implemented fixes on branch `ci/2026-05-29-ci-audit`, with real CI on `main`'s eventual merge going green.

## Boundaries / non-goals

- No local GitHub-Actions runner (`act` is not installed), so validation is: static reasoning over configs, the live failing-run logs, and **real CI runs triggered by pushing the branch**. Nix/Linux-only jobs are validated through CI, not Windows-local.
- Pre-existing test failures unrelated to CI configuration (e.g. the osmotic `booklogic` stale-cljs test, a book-compose persona test) are in scope only insofar as they block `main` going green; where a green `main` requires fixing them, that is P0, otherwise they are flagged, not silently absorbed.
- No change to product/skill behavior beyond what is required to make a gate honest or a job pass legitimately (no disabling checks to force green).

## Success criteria

- Every committed finding survived adversarial verification with cited evidence (file/line or run-log).
- All four persona lenses covered; cross-persona conflicts explicitly resolved in the synthesis.
- `main` CI reaches green by legitimate fixes (no check disabled to fake it), and the P1/P2 hardening is applied and validated against real runs.
