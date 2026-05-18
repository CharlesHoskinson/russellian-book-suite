# Change: tier4-cross-os-ci-matrix

**Tier:** 4 of 4
**Branch:** `feat/tier4-cross-os-ci-matrix`
**Depends on:** none

## Why

`.github/workflows/ci.yml` runs every job on `ubuntu-24.04`. The
python-skill matrix is Linux-only; the nix preflight is Linux-only;
`flake.nix` declares `flake-utils.lib.eachDefaultSystem` but the only
system that actually exercises the toolchain is `x86_64-linux`. The
audit surfaced cross-platform fragility that the current CI cannot
catch:

- **Regex semantics:** `re.search(pat, text, re.IGNORECASE | re.DOTALL)`
  in `ingest_ledger.py` matches differently across Python builds when
  the regex contains Unicode property escapes (`\p{L}`); the bundled
  Python on macOS/Windows is the same CPython, but locale defaults
  differ.
- **Path separators:** several scripts manipulate `Path` strings and
  intermittently fall through to `str.split("/")` — works on Linux,
  silently wrong on Windows.
- **Line endings:** `read_edn_file` uses default text mode; on
  Windows the universal-newline conversion changes file hashes,
  breaking the golden round-trip tests.

The framework is positioned for general-purpose use; authors using
macOS (most of the team) and Windows (the user) have no CI signal
today. Add a matrix: macOS-latest, Ubuntu-24.04, Windows-2022.

Rust verifier builds run on Linux + macOS only — Windows has known
libz3 packaging gaps that pre-date this change and warrant a separate
investigation. Document the gap with a runbook + a WSL fallback path
so Windows authors have an immediate workaround.

## What

- Expand `.github/workflows/ci.yml::python-skill-matrix` to `runs-on:
  ${{ matrix.os }}` with `os: [ubuntu-24.04, macos-latest, windows-2022]`.
- Add a `verifier-cargo-test` job that runs on Linux + macOS only;
  document the Windows skip in `docs/operations/ci-platforms.md`.
- Extend `flake.nix` to declare `darwin` system support so macOS
  developers can `nix develop` locally.
- Add a divergence-detection step to the `required` aggregator: if a
  Python test passes on one OS and fails on another, surface the
  divergence in the summary rather than hiding it inside the failed
  job's logs.
- Add an optional `windows-wsl-fallback` job that runs the Linux
  preflight inside WSL-Ubuntu on the `windows-2022` runner, via the
  `Vampire/setup-wsl@v3` GitHub Action, for authors who need a
  Windows-native CI signal before libz3-windows ships.

## Capabilities touched

- `ci-platform` — ADD (new capability, REQ-CI-040..044)

## Implementation notes

See `docs/plans/2026-05-18-tier234-and-usefulness.md`, Phase K.

## Acceptance

- The python-skill matrix shows 3 OS columns × N skills in the CI UI.
- The `verifier-cargo-test` matrix shows 2 OS columns (Linux, macOS).
- `nix develop` succeeds on a macOS developer machine and runs `make
  preflight` without modification.
- A test failure unique to one OS produces a CI summary line of the
  form `python-skill (book-qa): PASS on linux+mac, FAIL on windows`
  visible without expanding the per-job logs.
- `docs/operations/ci-platforms.md` exists and documents the libz3
  gap, the WSL fallback, and the divergence-summary mechanism.
