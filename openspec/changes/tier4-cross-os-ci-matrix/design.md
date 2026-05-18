# Design: tier4-cross-os-ci-matrix

## Matrix shape

```yaml
python-skill-matrix:
  name: python-skill (${{ matrix.skill }} / ${{ matrix.os }})
  runs-on: ${{ matrix.os }}
  strategy:
    fail-fast: false
    matrix:
      os: [ubuntu-24.04, macos-latest, windows-2022]
      skill:
        - book-qa
        - book-thesis
        - book-knowledge
        - book-review
        - russellian-style
        - review-conductor
      include:
        - skill: book-compose
          siblings: book-knowledge russellian-style book-review review-conductor
          pytest-deselect: "--deselect tests/test_sibling_skills.py::test_sibling_python_uses_skill_venv"
        - skill: neurosym-forge
          extra: dev
```

`fail-fast: false` is mandatory: we want every OS to report so the
divergence-summary has a complete picture.

The `include:` lines fan out across all three OS rows automatically
because the `os` axis is on `matrix:` (not `include:`).

## Symlink step — OS-portable

The current symlink step uses `ln -sfn`; on Windows this requires
either Developer Mode (for non-admin symlinks) or the `mklink /D`
command. The portable form uses `actions/github-script@v8` to call
`fs.symlinkSync` from Node, which works on all three runners without
extra setup:

```yaml
- name: symlink siblings
  if: matrix.siblings != ''
  uses: actions/github-script@v8
  with:
    script: |
      const { mkdirSync, symlinkSync } = require('fs');
      const { join } = require('path');
      const home = process.env.HOME || process.env.USERPROFILE;
      const target = join(home, '.claude', 'skills');
      mkdirSync(target, { recursive: true });
      const cwd = process.cwd();
      for (const s of '${{ matrix.siblings }}'.split(/\s+/).filter(Boolean)) {
        symlinkSync(join(cwd, 'skills', s), join(target, s), 'dir');
      }
```

## libz3 availability per platform

| OS            | libz3 source                   | Status          |
|---------------|--------------------------------|-----------------|
| ubuntu-24.04  | `apt install libz3-dev`        | works, baseline |
| macos-latest  | `brew install z3` + LDFLAGS    | works           |
| windows-2022  | none stable; sources hand-built| skip + runbook  |

Windows-native `libz3` builds exist (Microsoft ships them in some
Visual Studio component bundles), but the `z3-rs` crate's build.rs
hard-codes pkg-config probing, which doesn't reliably find them. A
proper fix requires upstreaming a `z3-rs` Windows codepath; until
then we skip and document.

## verifier-cargo-test job

```yaml
verifier-cargo-test:
  name: verifier-cargo-test (${{ matrix.verifier }} / ${{ matrix.os }})
  runs-on: ${{ matrix.os }}
  strategy:
    fail-fast: false
    matrix:
      os: [ubuntu-24.04, macos-latest]
      verifier: [bermuda, osmotic_pressure]
  steps:
    - uses: actions/checkout@v4
    - name: install z3 (linux)
      if: matrix.os == 'ubuntu-24.04'
      run: sudo apt-get install -y libz3-dev
    - name: install z3 (macos)
      if: matrix.os == 'macos-latest'
      run: brew install z3
    - uses: Swatinem/rust-cache@v2
      with:
        workspaces: verifiers/${{ matrix.verifier }}/rust-verifier
    - run: cargo test --features smt --manifest-path verifiers/${{ matrix.verifier }}/rust-verifier/Cargo.toml
```

The Linux Z3 install steps duplicate what `nix develop` already does
inside the `preflight` job; that's fine — this job is the
non-Nix path, mirroring how a developer on macOS without Nix would
invoke `cargo test` directly.

## Divergence summary (REQ-CI-042)

The existing `required` aggregator does a plain `contains(needs.*.result,
'failure')` check. Augment it to produce a markdown summary using
`$GITHUB_STEP_SUMMARY`:

```yaml
required:
  name: ci required
  needs: [preflight, python-skill-matrix, verifier-cargo-test]
  runs-on: ubuntu-24.04
  if: always()
  steps:
    - name: divergence summary
      run: |
        # Pull per-job results from the needs context, group by (skill,
        # verifier), and emit lines of the form
        # `python-skill (book-qa): PASS on linux+mac, FAIL on windows`
        # to $GITHUB_STEP_SUMMARY.
        python3 .github/scripts/divergence_summary.py
```

The `divergence_summary.py` script reads `${{ toJSON(needs) }}` via
an env-var hand-off and walks the per-OS results.

## flake.nix darwin support

`flake-utils.lib.eachDefaultSystem` already iterates over Linux +
macOS (it's `["x86_64-linux" "aarch64-linux" "x86_64-darwin"
"aarch64-darwin"]`), so the flake nominally supports darwin already.
The change is operational: add a darwin-specific note to the runbook
covering Homebrew prerequisites that are not present on a fresh
macOS, and add a CI step that exercises the darwin path on
`macos-latest` to catch flake-level regressions:

```yaml
- name: nix-flake-check (darwin)
  if: matrix.os == 'macos-latest'
  uses: DeterminateSystems/nix-installer-action@v22
- if: matrix.os == 'macos-latest'
  run: nix flake check
```

## WSL fallback runbook (REQ-CI-044)

For authors who need Windows-native CI signal without waiting for
libz3-windows:

```yaml
windows-wsl-fallback:
  if: ${{ vars.ENABLE_WINDOWS_WSL_FALLBACK == 'true' }}
  runs-on: windows-2022
  steps:
    - uses: actions/checkout@v4
    - uses: Vampire/setup-wsl@v3
      with:
        distribution: Ubuntu-24.04
    - shell: wsl-bash {0}
      run: |
        sudo apt-get update && sudo apt-get install -y libz3-dev python3-pip
        make preflight
```

The job is gated on a repository variable so it doesn't run on every
PR (WSL setup adds ~6 min to wall-clock). Authors enable it manually
when they want the signal.

## Operations doc

Create `docs/operations/ci-platforms.md` documenting:

1. The platform support matrix (which OS, which path).
2. The libz3-windows gap + the upstream `z3-rs` PR to track.
3. The WSL fallback runbook + how to enable it via the repo variable.
4. The divergence-summary format and how to interpret it.

This doc plays the same role as `docs/operations/sccache-followup.md`
plays for the sccache gap: a single linkable destination for
operational state on an open platform issue.
