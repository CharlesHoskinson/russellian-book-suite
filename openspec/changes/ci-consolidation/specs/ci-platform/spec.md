# Capability delta: ci-platform — change: ci-consolidation

Deltas against the `ci-platform` capability introduced by
`tier4-cross-os-ci-matrix` (REQ-CI-040..044).

## MODIFY

### REQ-CI-040 — Ubiquitous

The python-skill matrix SHALL be defined in
`.github/ci/skills-matrix.json` as the single source of truth, with
`defaults.os = [ubuntu-24.04, macos-15, windows-2022]`, and the
`python-skill-matrix` job in `.github/workflows/ci.yml` SHALL consume it
via `runs-on: ${{ matrix.os }}` with `fail-fast: false`.

**Rationale:** unchanged (cross-OS signal at PR time). The matrix moves
out of workflow YAML because the skill list was registered in four
hand-synced places (ci.yml axis, ci.yml includes, nightly duplicate,
check_windows_canary's YAML parser), and three skills have historically
landed unregistered. **Tested by:**
`verifiers/osmotic_pressure/tests/test_ci_matrix_shape.py` (re-pointed at
the JSON) and `ci/test_skills_matrix.py`.

## ADD

### REQ-CI-045 — Ubiquitous

Every directory under `skills/` SHALL be registered in
`.github/ci/skills-matrix.json`, either as a runnable matrix entry or as
`"ci": "none"` with a non-empty `reason`; a lint test in `ci/` SHALL fail
when a skill directory is unregistered, a registered entry has no
directory, or a runnable non-smoke entry with a Windows leg has no
`windows_canary`-marked test.

**Rationale:** feynman-style, halmos, and iacr-review each landed with
zero CI signal because registration was manual. **Tested by:**
`ci/test_skills_matrix.py`.

### REQ-CI-046 — Event-driven

When the `ci` workflow runs on a `pull_request` event, the
`compute-matrix` job SHALL select only skills whose `skills/<skill>/`
paths intersect the PR diff; when any changed path matches the configured
`shared_paths`, or the event is `push`, `merge_group`, or
`workflow_dispatch`, it SHALL select the full matrix. If selection cannot
be computed, the job SHALL fail (fail-closed via the `ci-required`
aggregator).

**Rationale:** a one-skill PR currently pays 38 legs (12 skills × 3 OSes
plus smokes); macOS legs dominate queue time. Main pushes and the merge
queue always validate the full matrix, so nothing lands unverified.
**Tested by:** `ci/test_compute_matrix.py`.

### REQ-CI-047 — Unwanted behaviour

IF a model warm-up (HuggingFace model or spaCy wheel) succeeds in a CI
job, THEN the corresponding cache SHALL be saved by an explicit
`actions/cache/save` step gated on the restore result — not by the
post-job hook — so the cache persists even when a later step in the job
fails; and the warm-up SHALL retry with exponential backoff
(15/30/60/120s) before failing the leg.

**Rationale:** `actions/cache`'s post-job save is skipped on job failure,
so a cold cache plus an HF 429 created a self-sustaining red loop on the
Windows neurosym-forge leg (runs 26973979791, 26985818903, 26986518016).
**Tested by:** shape assertions in
`verifiers/osmotic_pressure/tests/test_ci_matrix_shape.py`
(`cache/restore` + `cache/save` present in the `setup-models` composite).

### REQ-CI-048 — Ubiquitous

The `ci-budget` workflow SHALL trigger only on
`pull_request: types: [labeled]`, its existing weekly `schedule`, and
`workflow_dispatch`.

**Rationale:** the previous `[labeled, opened, synchronize]` trigger with
a job-level label gate produced 4–6 skipped phantom runs per PR push,
burying real runs in the checks list. **Tested by:**
`verifiers/osmotic_pressure/tests/test_ci_matrix_shape.py::test_budget_triggers_labeled_only`.
