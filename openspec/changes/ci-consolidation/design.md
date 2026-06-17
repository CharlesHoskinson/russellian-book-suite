# Design: ci-consolidation

## 1. Green — kill the HF 429 flake

**Problem shape.** `actions/cache@v5` restores in a pre-step and saves in a
post-step, but the post-step save is skipped when the job fails. The warm
step is the only thing between a cold cache and the flaky network, so:
cold cache → warm fails on 429 → job fails → cache not saved → next run is
also cold. The Windows leg of `neurosym-forge` is stuck in this loop.

**Fix.** In the new `setup-models` composite action (§3):

- `actions/cache/restore` (id: `restore-hf`) replaces the combined action.
- The warm step runs only on a restore miss, with exponential backoff:
  4 attempts, sleeping 15/30/60/120s between them (~4 min worst case;
  HF's anonymous 429 window is typically 60–120s).
- `actions/cache/save` runs immediately after a successful warm, gated on
  `steps.restore-hf.outputs.cache-hit != 'true'`. Because it is an explicit
  step (not a post-job hook), the model is persisted even if pytest later
  fails — one successful warm anywhere ends the death spiral for that OS.
- The pytest step keeps `HF_HUB_OFFLINE=1` exactly as today.
- The spaCy wheel cache gets the same restore/save split (same failure
  shape, milder blast radius).

`neurosym-forge` matrix legs get `timeout-minutes: 20` (the backoff can add
~4 min to the worst case; the current 15 is already tight on Windows).

## 2. Faster — per-skill dynamic PR matrix

**Single source of truth: `.github/ci/skills-matrix.json`.** One entry per
`skills/*` directory. Schema (all fields optional except `skill`):

```json
{
  "shared_paths": [
    ".github/workflows/ci.yml",
    ".github/actions/**",
    ".github/ci/skills-matrix.json",
    "ci/**"
  ],
  "defaults": { "os": ["ubuntu-24.04", "macos-15", "windows-2022"], "extra": "ci" },
  "skills": [
    { "skill": "book-qa", "constraints": "skills/book-qa/constraints.txt" },
    { "skill": "book-thesis" },
    { "skill": "book-knowledge" },
    { "skill": "book-review" },
    { "skill": "book-compose",
      "siblings": ["book-knowledge", "russellian-style", "book-review", "review-conductor"],
      "spacy": true,
      "pytest_deselect": "--deselect tests/test_sibling_skills.py::test_sibling_python_uses_skill_venv" },
    { "skill": "russellian-style", "spacy": true },
    { "skill": "feynman-style", "spacy": true },
    { "skill": "halmos" },
    { "skill": "iacr-review" },
    { "skill": "review-conductor" },
    { "skill": "neurosym-forge", "extra": "dev,semantic",
      "hf_model": "sentence-transformers/all-MiniLM-L6-v2",
      "pytest_workers": "auto", "timeout": 20 },
    { "skill": "paragraph-weaver" },
    { "skill": "scrapling-fetch", "os": ["ubuntu-24.04"], "extra": "none", "smoke": "import" },
    { "skill": "syntopical-metabook", "os": ["ubuntu-24.04"], "extra": "none", "smoke": "import" },
    { "skill": "iacr-math-prose", "ci": "none",
      "reason": "reference/template-only skill; no Python package, no tests (AGENTS.md)" }
  ]
}
```

**`compute-matrix` job.** Runs `python -m ci.compute_matrix` (stdlib-only,
no Nix) which:

1. Reads the JSON.
2. On `pull_request`: computes changed files via
   `git diff --name-only origin/$BASE...HEAD` (the job checks out with
   `fetch-depth: 0`). A skill is *selected* if any changed path starts with
   `skills/<skill>/`. If any changed path matches `shared_paths`, or the
   event is `push`/`merge_group`/`workflow_dispatch`, **all** skills are
   selected (fail-open to the full matrix).
3. Expands selected entries × their `os` list into a flat
   `{"include": [...]}` matrix and writes `matrix` plus a boolean
   `any_selected` to `$GITHUB_OUTPUT`.

`python-skill-matrix` consumes it:

```yaml
needs: [compute-matrix]
if: needs.compute-matrix.outputs.any_selected == 'true'
strategy:
  fail-fast: false
  matrix: ${{ fromJSON(needs.compute-matrix.outputs.matrix) }}
```

The `changes` job's `python` paths-filter output is retired (subsumed);
its `rust` output stays for `preflight`/`cargo-test` gating.

**Registration invariant (REQ-CI-045).** A new test in `ci/`
(runs inside the always-on lint job's existing `pytest ci/ -q`):

- every directory under `skills/` appears in the JSON exactly once;
- every JSON entry points at an existing directory;
- entries are either runnable (legs) or `"ci": "none"` with a non-empty
  `reason`;
- runnable non-smoke entries with a Windows leg must have ≥1
  `windows_canary`-marked test (this ports `ci/check_windows_canary.py`
  from hand-parsing ci.yml YAML to reading the JSON — the workflow keeps
  invoking `python -m ci.check_windows_canary`).

## 3. Modular — composite actions

**`.github/actions/symlink-siblings/action.yml`** — input `siblings`
(space-separated). Body is the existing `github-script` block, moved
verbatim. Consumed by `ci.yml` and `nightly-flake-drift.yml` (today the
block is copy-pasted between them).

**`.github/actions/setup-models/action.yml`** — inputs `spacy`
(true/false) and `hf-model` ('' = skip). Contains the spaCy wheel
restore/download/save + install, and the HF restore/warm/save from §1.
The matrix job invokes it with values derived from the matrix entry
(`matrix.spacy`, `matrix.hf_model`), so the per-skill `if:` chains on
skill names disappear from the workflows.

The bash `retry()` helper lives inside `setup-models`; the remaining
inline retries (actionlint tarball, apt/brew in cargo-test) stay where
they are — each has exactly one call site.

Net effect: `ci.yml` loses the symlink JS, the spaCy block, the HF block,
and the static matrix tables (~150 lines); the nightly loses its
duplicates of all of the above.

## 4. Maintainable — delete ci-legacy.yml

Coverage disposition (each ci-legacy job, where its signal goes):

| ci-legacy job | Disposition |
|---|---|
| `lint-workflow` (actionlint) | already in `ci.yml` |
| `test-*` × py3.11/3.12 | → nightly: `python-version` axis `[3.11, 3.12]`, Linux-only, driven by the same skills-matrix.json (skills claim `requires-python >=3.11`; today 3.11/3.12 are tested nowhere) |
| `test-*` × py3.13 | already in `ci.yml` (3-OS matrix) |
| `smoke-bermuda-pipeline` (compile_thesis + consistency_cozo on `examples/bermuda-manual`) | → nightly job `bermuda-example-pipeline` (not covered by preflight, which smokes the *verifier*, not the book-thesis pipeline) |
| `bermuda-informational` | dropped — `continue-on-error` on every step; verifies nothing |
| `cljs-bermuda-test` (shadow-cljs compile test + node test.js) | → nightly job `cljs-bermuda-test` (preflight's `make -C verifiers/bermuda ci` builds the cljs release but never runs the cljs tests) |
| `bermuda-z3-build` | covered by `cargo-test` (`--features smt` builds before testing) |
| `bermuda-z3-verify` | dropped — every assertion step is `\|\| true` / `continue-on-error` / `--stub`; advisory theater |
| `osmotic-pressure-smoke` | covered by preflight (`make -C verifiers/osmotic_pressure ci`) |

**Guard-test updates required by the deletion and the JSON migration**
(all in the same change, or preflight breaks):

- `verifiers/osmotic_pressure/tests/test_ci_matrix_shape.py`:
  - `_legacy_text()` + `test_legacy_bermuda_z3_job_name_not_misleading`
    are deleted (their target file is gone).
  - `test_python_skill_matrix_has_three_oses`,
    `test_python_skill_include_overrides_are_in_skill_axis`,
    `test_coverage_gap_skills_have_smoke_legs` re-point at
    `skills-matrix.json` (assert the three OS labels in `defaults.os`,
    assert book-compose/neurosym-forge are runnable entries, assert the
    two smoke entries) — same REQ IDs, new source of truth.
  - `test_python_skill_runs_on_matrix_os`, fail-fast, cargo-test,
    divergence, dependabot, and ci-budget tests are unaffected (those
    constructs remain in `ci.yml` text).
- `verifiers/bermuda/tests/test_axioms_lockstep.py::test_ci_yaml_has_bermuda_z3_jobs`
  is rewritten to assert what the suite actually guarantees now: `ci.yml`
  has a `cargo-test` job whose matrix includes `bermuda` and whose run line
  carries `--features smt`. The corresponding `--deselect` is removed from
  `verifiers/bermuda/Makefile`'s `smoke` target (this Makefile is *not*
  covered by `scripts/ci-steps.txt`, which only pins the top-level
  preflight recipe lines — `make -C verifiers/bermuda ci` is the unit).

## 5. Noise — ci-budget triggers

`on.pull_request.types` narrows from `[labeled, opened, synchronize]` to
`[labeled]` (+ existing `workflow_dispatch`). The job-level label check
stays as a second gate. This removes the 4–6 skipped phantom runs per PR
push. The existing guard tests on ci-budget content are unaffected.

## 6. Guardrails preserved

- `ci-required` keeps its name, its `needs` list (gaining
  `compute-matrix` in the always-run `require_success` set), and its
  fail-closed semantics. `python-skill-matrix` stays in
  `require_not_failed` (it may legitimately skip when `any_selected` is
  false — docs-only PRs).
- The ruleset context and `scripts/check-required-name.sh` are untouched.
- `actionlint` (always-run job) validates the rewritten YAML at PR time.
- The flake-drift check is untouched (no top-level Makefile changes).
- nightly keeps its red-run alerting job; new nightly jobs feed it.

## Error handling

- `compute_matrix.py` fails closed: unparseable JSON, a git diff error, or
  zero parsed skills on a push event → non-zero exit → `compute-matrix`
  job fails → `ci-required` fails (it is in the `require_success` set).
- `setup-models` warm failure after all backoff attempts fails the leg
  (as today) — but a *previously* warmed cache can no longer be lost.

## Testing

- `ci/test_compute_matrix.py`: selection logic (single-skill PR, multi-skill
  PR, shared-path PR → full, push → full, docs-only → empty/any_selected
  false), output shape (include rows carry os/extra/siblings/deselect/
  workers/smoke fields), fail-closed paths.
- Registration lint tests as in §2.
- Updated guard tests as in §4.
- End-to-end: the PR for this change touches shared paths, so it must
  itself run the full matrix — which simultaneously verifies the dynamic
  matrix and re-greens the Windows neurosym leg via the §1 cache fix.
