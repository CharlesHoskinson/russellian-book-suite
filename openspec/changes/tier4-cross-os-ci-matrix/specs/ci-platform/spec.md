# Capability delta: ci-platform — change: tier4-cross-os-ci-matrix

This change introduces the `ci-platform` capability, which governs the
operating-system reach of the GitHub Actions CI matrix and the
operational documentation for per-platform support gaps.

## ADD

### REQ-CI-040 — Ubiquitous

The `python-skill-matrix` job in `.github/workflows/ci.yml` SHALL run
on every OS in `[ubuntu-24.04, macos-latest, windows-2022]` via a
`matrix.os` axis with `runs-on: ${{ matrix.os }}` and
`fail-fast: false`.

**Rationale:** Authors developing on macOS or Windows currently
receive no CI signal. Path-separator, regex-semantics, and
line-ending differences silently break the framework on those
platforms; the matrix surfaces the divergence at PR time rather than
at first-author time. **Tested by:**
existence-and-shape check in `.github/scripts/test_ci_yaml.py::test_python_skill_matrix_has_three_os`
(added in K1.1)

### REQ-CI-041 — Ubiquitous

The `verifier-cargo-test` job in `.github/workflows/ci.yml` SHALL run
on `[ubuntu-24.04, macos-latest]` and SHALL NOT run on
`windows-2022`; the Windows skip SHALL be documented in
`docs/operations/ci-platforms.md` with a reference to the upstream
libz3-windows gap.

**Rationale:** The `z3-rs` crate's pkg-config probe doesn't reliably
find the Microsoft-shipped libz3 on Windows runners; until a `z3-rs`
Windows codepath ships upstream, attempting Windows cargo test
produces a confusing link error rather than a real signal. Skipping
with a documented reason is more honest than hiding the failure.
**Tested by:** existence checks in
`.github/scripts/test_ci_yaml.py::test_verifier_cargo_test_skips_windows`
and `tests/test_ci_platforms_doc.py::test_ci_platforms_doc_documents_windows_skip`
(added in K2.1, K5.1)

### REQ-CI-042 — Unwanted behaviour

IF a Python test passes on one OS in the python-skill matrix but
fails on another, THEN the `required` aggregator job SHALL emit a
divergence-summary line of the form
`python-skill (<skill>): PASS on <ok-os-set>, FAIL on <bad-os-set>`
to `$GITHUB_STEP_SUMMARY` so the divergence is visible on the PR
summary page without expanding any per-job logs.

**Rationale:** Without a divergence summary, an author seeing a red
PR has to manually expand each job and compare results across the
matrix to figure out which OS broke. The summary surfaces the
divergence in one glance and makes "passes on Linux, fails on
Windows" an immediately-readable signal. **Tested by:**
`.github/scripts/test_divergence_summary.py::test_pass_one_fail_other_emits_divergence_line`
(added in K4.3)

### REQ-CI-043 — Ubiquitous

The `flake.nix` SHALL declare support for darwin systems alongside
the existing linux systems (which `flake-utils.lib.eachDefaultSystem`
already provides), and `docs/operations/neurosym-forge-runbook.md`
SHALL include a "Working on macOS" section covering Homebrew
prerequisites and `nix develop` entry.

**Rationale:** Most of the team develops on macOS. The flake is the
single source of toolchain truth; without a darwin-supported flake
and a runbook entry, macOS developers cannot reproduce the hermetic
environment that CI uses, leaking the "works on my machine"
class of bug. **Tested by:** existence check in
`tests/test_flake_supports_darwin.py::test_flake_check_passes_on_macos`
(added in K3.1)

### REQ-CI-044 — Optional feature

WHERE the repository variable `ENABLE_WINDOWS_WSL_FALLBACK` is set to
`true`, the workflow SHALL run an additional `windows-wsl-fallback`
job on `windows-2022` that executes `make preflight` inside
WSL-Ubuntu via the `Vampire/setup-wsl@v3` GitHub Action. The
enablement procedure SHALL be documented in
`docs/operations/ci-platforms.md`.

**Rationale:** Until libz3-windows ships and the verifier-cargo-test
job can cover Windows directly, authors who need a Windows-native CI
signal can opt in to a WSL fallback. Gating on a repo variable
keeps the ~6-minute WSL setup cost off the default PR path while
making it one-toggle-away when needed. **Tested by:**
existence check in `.github/scripts/test_ci_yaml.py::test_wsl_fallback_job_gated_on_repo_variable`
and runbook check in `tests/test_ci_platforms_doc.py::test_ci_platforms_doc_includes_wsl_runbook`
(added in K6.1, K5.1)
