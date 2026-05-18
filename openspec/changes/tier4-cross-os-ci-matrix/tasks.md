# Tasks: tier4-cross-os-ci-matrix

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase K for full
TDD steps. Task numbers correspond 1:1.

## Phase K.1 — Add OS axis to python-skill matrix

- [ ] K1.1: Edit `.github/workflows/ci.yml::python-skill-matrix` to add the `os: [ubuntu-24.04, macos-latest, windows-2022]` axis and switch `runs-on: ${{ matrix.os }}`. (REQ-CI-040)
- [ ] K1.2: Replace the `ln -sfn` symlink step with the portable `actions/github-script@v8` form so the step works on Windows. (REQ-CI-040)
- [ ] K1.3: Push a draft PR and observe which skills are red on which OS; fix the first wave of trivially-Windows-broken paths (e.g., `os.path.join` substitutions, `encoding="utf-8"` adds). (REQ-CI-040)
- [ ] K1.4: Commit the workflow + skill fixes.

## Phase K.2 — Add verifier-cargo-test job

- [ ] K2.1: Add the `verifier-cargo-test` job with `os: [ubuntu-24.04, macos-latest]` and per-OS Z3 install steps (`apt` for Linux, `brew` for macOS). (REQ-CI-041)
- [ ] K2.2: Add `verifier-cargo-test` to the `required` aggregator's `needs:` list. (REQ-CI-041)
- [ ] K2.3: Commit.

## Phase K.3 — flake.nix darwin support

- [ ] K3.1: Confirm `flake-utils.lib.eachDefaultSystem` already enumerates darwin systems; add a `nix flake check` step gated on `matrix.os == 'macos-latest'` inside the python-skill-matrix to exercise the flake on darwin in CI. (REQ-CI-043)
- [ ] K3.2: Add a "Working on macOS" section to `docs/operations/neurosym-forge-runbook.md` covering Homebrew prerequisites (`brew install z3 nix`). (REQ-CI-043)
- [ ] K3.3: Commit.

## Phase K.4 — Divergence summary

- [ ] K4.1: Add `.github/scripts/divergence_summary.py` that reads `NEEDS_JSON` (env var, fed `${{ toJSON(needs) }}`) and emits per-(skill, OS) PASS/FAIL lines to `$GITHUB_STEP_SUMMARY`. (REQ-CI-042)
- [ ] K4.2: Wire the script into the `required` aggregator job. (REQ-CI-042)
- [ ] K4.3: Add `tests/test_divergence_summary.py` that feeds a synthetic `NEEDS_JSON` and asserts the expected summary lines. (REQ-CI-042)
- [ ] K4.4: Commit.

## Phase K.5 — `docs/operations/ci-platforms.md`

- [ ] K5.1: Author `docs/operations/ci-platforms.md` covering: platform matrix, libz3-windows gap, WSL fallback runbook, divergence-summary format. Pattern after `docs/operations/sccache-followup.md`. (REQ-CI-041, REQ-CI-042, REQ-CI-044)
- [ ] K5.2: Link the new doc from the top-level README's "operations" section.
- [ ] K5.3: Commit.

## Phase K.6 — WSL fallback (optional, gated)

- [ ] K6.1: Add the `windows-wsl-fallback` job gated on `vars.ENABLE_WINDOWS_WSL_FALLBACK == 'true'`. (REQ-CI-044)
- [ ] K6.2: Test the gate works: with the variable unset, the job is skipped; with it set, the job runs `make preflight` inside WSL-Ubuntu. (REQ-CI-044)
- [ ] K6.3: Document the enablement procedure in `docs/operations/ci-platforms.md`. (REQ-CI-044)
- [ ] K6.4: Commit.

## Phase K.7 — Open PR

- [ ] K7.1: Push branch `feat/tier4-cross-os-ci-matrix` and open PR.
- [ ] K7.2: Merge on green CI.
