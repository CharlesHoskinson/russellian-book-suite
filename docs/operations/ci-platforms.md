# CI platforms runbook

## Status

The CI matrix runs across three operating systems as of PR-tier4-L
(2026-05-18). This doc is the single source of truth for the
per-platform support story: which jobs run where, how libz3 is
acquired, why one cell is intentionally empty, and what the
WSL-fallback recipe looks like for Windows contributors who need
cargo signal locally.

## Matrix snapshot

| Job                  | Linux (ubuntu-24.04) | macOS (macos-15) | Windows (windows-2022)        |
|----------------------|----------------------|----------------------|-------------------------------|
| `python-skill-matrix`| nix-supplied Python  | `actions/setup-python` | `actions/setup-python`      |
| `preflight` (nix)    | yes                  | no (Linux-only)      | no (Linux-only)               |
| `cargo-test`         | flake rust shell     | flake rust shell     | **skipped — see below**       |
| `ci-divergence-summary` | linux runner (aggregator only) | n/a | n/a                |

`fail-fast: false` is set on every matrix job. We want every leg to
report — otherwise the divergence-summary has incomplete data.

The table above is x86_64-only; the per-PR matrix never builds the
`aarch64-linux` system the flake declares in its `supportedSystems`
list. The nightly `nightly.yml` workflow closes that gap with a
single `flake-check-arm` leg (`ubuntu-24.04-arm`, nightly-only,
`nix flake check`). ARM GitHub-hosted runners are free for public
repos (GA 2025-08), so the arch the flake claims to support is
exercised once daily rather than never.

| Job               | Arch          | OS / runner       | Cadence       | Check             |
|-------------------|---------------|-------------------|---------------|-------------------|
| `flake-check-arm` | aarch64-linux | `ubuntu-24.04-arm`| nightly-only  | `nix flake check` |

## z3 and toolchain in CI

As of nix-consolidation PR 3, the `cargo-test` job takes both its Rust
toolchain and its z3 library from the flake's `rust` devShell
(`nix develop .#rust`). This replaces the previous per-OS apt/brew
installs. The `preflight` job was already hermetic; `cargo-test` now
matches it. One pinned solver version links everywhere.

## libz3 install — local, non-nix contributors

Developers who do not have nix available can still run the verifier
tests manually by installing libz3 from their system package manager.
These are **local fallback recipes only** — CI no longer uses them.

### Linux (ubuntu-24.04)

```bash
sudo apt-get install -y libz3-dev
cargo test --features smt --manifest-path verifiers/<name>/rust-verifier/Cargo.toml
```

### macOS

```bash
brew install z3
cargo test --features smt --manifest-path verifiers/<name>/rust-verifier/Cargo.toml
```

The Homebrew bottle ships both the shared dylib and the headers; the
`z3` crate's pkg-config probe finds them without extra `LDFLAGS` on
modern macOS.

### Windows (windows-2022)

There is no supported install path today; the `cargo-test` job
deliberately omits Windows. See the next section.

## Why Windows cargo is skipped

Three options were evaluated, all rejected:

1. **`vcpkg install z3`** — produces a libz3 build but the resulting
   `.lib` does not match the bindgen-generated header the `z3` crate
   expects without manual patching of the crate's build.rs. Brittle
   under crate version updates.
2. **Microsoft's upstream Z3 MSI** — ships an executable, not the
   static lib or headers the `z3` crate needs.
3. **Building libz3 from source on the Windows runner** — adds ~10
   minutes of wall-clock to every PR and produces a build that the
   crate's pkg-config probe doesn't find without environment surgery
   we'd then have to maintain.

The honest signal is "Windows cargo is unsupported at the moment;
use the WSL fallback if you need cargo signal locally". The
`python-skill-matrix` still runs on Windows, which covers the bulk
of the test surface.

If `z3-rs` ships a Windows codepath upstream that handles libz3
discovery natively, revisit this decision and add the Windows leg
back to the `cargo-test` matrix.

## WSL fallback for Windows contributors

Windows contributors who need a Windows-host cargo signal can run the
full Linux preflight chain inside WSL2 Ubuntu. This is the same
toolchain CI uses on `ubuntu-24.04`, so a green WSL preflight is a
proxy for a green Linux CI leg.

### One-time setup

```powershell
# In an admin PowerShell:
wsl --install -d Ubuntu-24.04
# Reboot when prompted, then:
wsl -d Ubuntu-24.04
```

Inside WSL Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential pkg-config libz3-dev \
    python3 python3-pip python3-venv \
    curl git make
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain 1.90.0
. "$HOME/.cargo/env"
```

Optional but recommended: install nix inside WSL so `nix develop -c
make preflight` works (matching the CI preflight job exactly):

```bash
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install --no-confirm
. /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
```

### Running CI-equivalent checks inside WSL

```bash
# From a Windows host clone at C:\work\russellian-book-suite,
# WSL sees it at /mnt/c/work/russellian-book-suite.
cd /mnt/c/work/russellian-book-suite

# Full preflight (nix path; mirrors the Linux preflight job exactly):
nix develop -c make preflight

# Or just cargo-test (no nix needed):
cargo test --features smt --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml
cargo test --features smt --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml
```

### Notes on file-system performance under WSL

Builds inside `/mnt/c/...` are 3-5× slower than builds on the WSL
ext4 filesystem (e.g., `~/work/...`). For an iteration-heavy debug
session, `git clone` the repo into the WSL home directory instead of
working off the Windows mount.

## Optional `windows-wsl-fallback` job

The workflow can be configured to run `make preflight` inside
WSL-Ubuntu on the `windows-2022` runner. This is gated on a
repository variable to keep the ~6-minute WSL setup cost off every
PR:

1. **Enable.** In repo settings → Secrets and variables → Actions →
   Variables, set `ENABLE_WINDOWS_WSL_FALLBACK = true`.
2. **Trigger.** Re-run the workflow (or open a new PR). The
   `windows-wsl-fallback` job appears in the matrix.
3. **Disable.** Unset the variable; the job goes back to being
   skipped.

This job is not in `ci.yml` as of the L-phase PR; it ships as a
follow-up if/when the team decides the ~6-minute cost is worth the
signal. The skeleton lives in `openspec/changes/tier4-cross-os-ci-matrix/design.md`
§ "WSL fallback runbook" for the future PR.

## Divergence-summary format

The `ci-divergence-summary` job runs after `python-skill-matrix` and
`cargo-test` complete (regardless of pass/fail) and emits a markdown
table to `$GITHUB_STEP_SUMMARY`. The table looks like:

```
## Per-OS CI divergence

| Job          | Linux | macOS    | Windows                       |
|--------------|-------|----------|-------------------------------|
| python-skill | pass  | pass     | see legs                      |
| cargo-test   | pass  | see legs | n/a (REQ-CI-044: WSL fallback)|
```

Cell values:

- `pass`   — every matrix leg under that job/OS combination passed.
- `see legs` — at least one leg under that job/OS failed; open the
  matrix on the run page for per-skill / per-verifier detail.
- `skip` / `cancel` — the parent job was skipped or cancelled.
- `n/a`    — the matrix does not exercise that OS (e.g., Windows
  cargo-test).

GitHub Actions exposes `needs.<job>.result` as a single aggregate
across the whole matrix, not per-leg. A richer per-leg breakdown
would require parsing the workflow run via `gh api`. That's deferred;
the at-a-glance summary is enough to answer "did the matrix
diverge?" in one glance.

## Local matrix testing via `act`

`act` (https://github.com/nektos/act) runs GitHub Actions workflows
locally under Docker. The Linux legs work out of the box:

```bash
# Run a single job (Linux only):
act -j python-skill-matrix --matrix os:ubuntu-24.04 --matrix skill:book-qa

# Run the cargo-test job:
act -j cargo-test --matrix os:ubuntu-24.04 --matrix verifier:osmotic_pressure
```

`act` does **not** support macOS or Windows runners locally — those
require host machines of the respective OS. To exercise the macOS
matrix locally, run `nix develop -c make preflight` on a macOS
machine; to exercise the Windows matrix locally, use the WSL
fallback above.

## Recovering from a per-OS divergence

When the divergence-summary shows "Linux pass, macOS fail" (or
similar), the debug recipe is:

1. Open the failing matrix leg on the run page; read the pytest /
   cargo test output.
2. The common platform-divergence root causes:
   - **Path separators.** Code that does `str.split("/")` instead of
     `pathlib.PurePath.parts`.
   - **Line endings.** Generated files written without
     `encoding="utf-8", newline=""` get auto-converted to CRLF on
     Windows; goldens then mismatch.
   - **Regex compilation.** `re.compile(pat, re.UNICODE)` works
     uniformly; `re.compile(pat)` with `\b` boundaries can differ on
     non-ASCII inputs across CPython locale settings.
   - **Shell-isms.** Tests that shell out to `bash -c ...` break on
     Windows. Use `subprocess.run([...], shell=False)`.
3. Reproduce locally: `nix develop -c pytest ...` on macOS; WSL
   `pytest ...` (with the local pip env) on Windows.
4. Fix and re-push.

## See also

- `openspec/changes/tier4-cross-os-ci-matrix/proposal.md` — why this
  matrix exists.
- `openspec/changes/tier4-cross-os-ci-matrix/design.md` — full job
  topology and per-job design notes.
- `flake.nix` — the `supportedSystems` constant; the canonical list
  of OS/arch combinations the flake supports.
- `docs/operations/sccache-followup.md` — the sister doc tracking
  the sccache re-enable runbook (same style; same role).
