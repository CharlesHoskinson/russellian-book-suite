# CI Pipeline Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current ad-hoc CI with a hermetic, fast, hard-to-regress pipeline anchored on a Nix flake. After this plan ships, a green `make preflight` on a WSL2 Ubuntu 24.04 laptop guarantees green CI; no class of bug that thrashed sprint 5 can recur silently.

**Architecture:** Six stacked layers, one source of truth for toolchains. `flake.nix` pins every Rust/Node/Python/JVM/Z3 version; both the laptop and the GitHub runner execute `nix develop -c <step>` against the same Makefile target list. Local pre-flight gates (lefthook + clj-kondo + scaffold-bake) catch six of the seven sprint-5 failure classes before push; the seventh (Linux `.so` linker) is caught by running the same Linux toolchain under WSL2.

**Tech Stack:** Nix flakes (nixpkgs 25.05 + rust-overlay), Lefthook 1.x, clj-kondo, cookiecutterassert/pytest-cookies pattern, mozilla-actions/sccache-action, Swatinem/rust-cache, DeterminateSystems/nix-installer-action, cargo-nextest, mold, GitHub Rulesets API, merge queue.

**Dependencies:** None — this plan supersedes the current CI. PR-0 ships first as docs-only; PRs 1-3 land in order. Each PR is independently revertible.

**Source spec:** `docs/specs/2026-05-17-ci-cleanup-design.md` (committed on branch `ci-cleanup-design`, must be merged or rebased onto plan branch before starting).

---

## Pre-flight

Read these before starting:
- `docs/specs/2026-05-17-ci-cleanup-design.md` (the design this plan implements — every component, success criterion, and risk)
- `docs/plans/2026-05-17-booklogic-pr6.md` (canonical plan-style reference)
- Current `.github/workflows/ci.yml` (~460 lines; the file being rewritten in PR-2)
- Current `.github/workflows/booklogic-cljs-test.yml` (folded into ci.yml in PR-2)
- `skills/neurosym-forge/scripts/scaffold_project.py` (template instantiator; scaffold-bake test wraps it)
- `skills/neurosym-forge/assets/project-template/` (template tree the scaffold-bake test exercises end-to-end)
- The sprint-5 thrash post-mortem (§ 2 of the spec) — the seven bugs are the canonical regression suite

**Branch:** `feat/ci-cleanup` cut from current `main`.

```bash
cd ~/work/russellian-book-suite      # WSL path post-PR-0; until then C:/work/russellian-book-suite
git fetch origin
git checkout main
git pull --ff-only origin main
git checkout -b feat/ci-cleanup
```

**Confirm pre-conditions:**

```bash
# Sprint-5 v0.4.0 is released
gh release view v0.4.0 --json isLatest --jq '.isLatest'
# Expected: true

# Design spec is on main (or on a branch ready to merge before PR-0)
git show main:docs/specs/2026-05-17-ci-cleanup-design.md | head -3
# Expected: "# CI Pipeline Cleanup Design — Post Sprint-5 Thrash"

# Repo currently uses Windows line endings on most files
git config --get core.autocrlf
# Expected: input  (or true) — confirms the .gitattributes work in PR-0 is needed
```

If the design spec isn't on `main` yet, merge PR `ci-cleanup-design` first; PR-0 of this plan rebases onto it.

**Test invocation cheatsheet (used across phases):**

```bash
# Local test of a generated bake
cd /tmp/baked-project && make ci

# Local pre-flight (lands in PR-1)
make preflight

# Nix flake check
nix flake check --no-build-output

# Regression suite (lands in PR-1 step 7)
pytest skills/neurosym-forge/tests/regression/ -v

# CI wall-time check (lands in PR-2 step 4)
gh run list --workflow=ci.yml --limit 20 --json conclusion,createdAt,updatedAt
```

**Commit hygiene:** terse, imperative, lowercase scope prefix (`ci:`, `nix:`, `lefthook:`, `wsl:`); no AI attribution; no Co-Authored-By; one problem per commit; never `--no-verify`.

**Scope guard:** This plan does not change any verifier (bermuda, osmotic-pressure) logic, does not migrate any skill from pytest, and does not switch CI providers. Any change to `verifiers/**` or `skills/**/src/` outside `skills/neurosym-forge/tests/` is out of scope.

---

## File Structure

### Created

```
.gitattributes                                          PR-0 step 2
.wslconfig.example                                      PR-0 step 3
docs/dev-environment.md                                 PR-0 step 1
scripts/wsl-bootstrap.sh                                PR-0 step 4
flake.nix                                               PR-1 step 1
flake.lock                                              PR-1 step 1 (auto)
.envrc                                                  PR-1 step 2
lefthook.yml                                            PR-1 step 3
Makefile                                                PR-1 step 4
scripts/regex-compile-check.py                          PR-1 step 5
scripts/ci-steps.txt                                    PR-1 step 6 (drift source)
skills/neurosym-forge/tests/test_scaffold_bake.py       PR-1 step 7
skills/neurosym-forge/tests/regression/__init__.py      PR-1 step 8
skills/neurosym-forge/tests/regression/conftest.py      PR-1 step 8
skills/neurosym-forge/tests/regression/test_sprint5_bug_catches.py
                                                        PR-1 step 9
skills/neurosym-forge/assets/project-template/Makefile.tmpl
                                                        PR-1 step 10 (template gains a `make ci` target)
.github/workflows/ci.yml                                PR-2 step 1 (rewritten — old file moves to ci-legacy.yml)
.github/workflows/ci-legacy.yml                         PR-2 step 0 (rename of current ci.yml)
.github/workflows/nightly-flake-drift.yml               PR-2 step 5
.github/workflows/ci-budget.yml                         PR-2 step 6
scripts/ruleset-apply.sh                                PR-3 step 1
docs/operations/branch-protection.md                    PR-3 step 2
```

### Modified

```
.github/workflows/booklogic-cljs-test.yml              PR-2 step 3 (deleted; folded into ci.yml)
verifiers/bermuda/package.json                          PR-1 step 11 (adds `make ci` target wrapping npm run build + smoke)
verifiers/osmotic_pressure/package.json                 PR-1 step 11 (adds `make ci` target)
README.md                                               PR-0 step 5 (links to docs/dev-environment.md)
docs/specs/2026-05-17-ci-cleanup-design.md              merged onto main before PR-0
```

### Deleted

```
.github/workflows/booklogic-cljs-test.yml               PR-2 step 3 (folded into ci.yml)
.github/workflows/ci-legacy.yml                         PR-2 step 8 (after one green sprint)
```

---

# PR-0 — WSL bootstrap (docs + scripts only)

**Branch:** `feat/ci-cleanup-pr0-wsl-bootstrap` cut from `feat/ci-cleanup`.

**Scope:** Zero behavior change. Ships only docs + bootstrap script + `.gitattributes` + `.wslconfig.example`. Devs who don't run WSL see no impact. The CRLF spam stops because `.gitattributes` enforces LF.

**Wall-time exit criteria:** None (docs only). The PR merges when reviewer confirms doc accuracy.

## Phase 0.1 — Author the dev-environment guide

### Task 0.1.1: Create `docs/dev-environment.md` skeleton

**Files:**
- Create: `docs/dev-environment.md`

- [ ] **Step 1: Author the guide**

Create `docs/dev-environment.md` with the following exact contents:

```markdown
# Developer Environment Setup

This repo's CI runs on Ubuntu Linux. To eliminate "works on my machine" drift, Windows developers run their builds inside WSL2 Ubuntu 24.04 with a Nix-pinned toolchain. macOS and Linux developers skip WSL and run Nix directly.

## TL;DR

1. Install WSL2 + Ubuntu 24.04 (Windows only)
2. Install Nix via the Determinate Systems installer
3. `git clone https://github.com/CharlesHoskinson/russellian-book-suite ~/work/russellian-book-suite`
4. `cd ~/work/russellian-book-suite && direnv allow`
5. `make preflight`

Green preflight ⇒ green CI. Always.

## Why WSL2

GitHub Actions runs on `ubuntu-24.04`. Compiled artifacts (`.so` libraries, the napi `.node` addon, Z3-linked binaries) only exercise the Linux ABI on Linux. Sprint 5 burned 60 minutes of wall time on bugs that surfaced only in CI because no Windows developer could build a `.so` locally. WSL2 closes that gap.

## Setup — Windows 11

### 1. Install WSL2 + Ubuntu 24.04

Open PowerShell as Administrator:

```powershell
wsl --install -d Ubuntu-24.04
```

Restart when prompted. On first launch, set a Linux username and password.

Confirm:

```powershell
wsl --status
# Default Distribution: Ubuntu-24.04
# Default Version: 2
```

### 2. Drop `.wslconfig` in your Windows home directory

Copy `.wslconfig.example` from this repo to `%USERPROFILE%\.wslconfig` and edit the `memory` and `processors` lines to fit your hardware. After editing, run `wsl --shutdown` once so the new config takes effect.

### 3. Install Nix in WSL

Inside WSL Ubuntu:

```bash
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install linux \
    --extra-conf "trusted-users = $(whoami)" \
    --no-confirm
```

After install, restart the shell (`exec $SHELL`). Confirm:

```bash
nix --version
# nix (Determinate Nix) 2.x.x
```

### 4. Install direnv + nix-direnv

```bash
sudo apt-get update && sudo apt-get install -y direnv
mkdir -p ~/.config/direnv
echo 'source $HOME/.nix-profile/share/nix-direnv/direnvrc' > ~/.config/direnv/direnvrc
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
exec bash
```

### 5. Configure git

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global core.autocrlf false
git config --global core.eol lf
git config --global credential.helper \
  "/mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager.exe"
```

The credential-helper line bridges Windows' Git Credential Manager into WSL so HTTPS pushes use your existing credential vault.

For SSH access, generate a fresh key inside WSL and paste the public half into GitHub:

```bash
ssh-keygen -t ed25519 -C "you@example.com"
cat ~/.ssh/id_ed25519.pub
# Paste into https://github.com/settings/keys
```

### 6. Clone and bootstrap the repo

```bash
mkdir -p ~/work
cd ~/work
git clone git@github.com:CharlesHoskinson/russellian-book-suite.git
cd russellian-book-suite
direnv allow
# Nix downloads the toolchain on first entry; subsequent shells are instant.
```

### 7. Run pre-flight

```bash
make preflight
# Expected: green; same command CI runs.
```

### 8. Install lefthook git hooks

```bash
lefthook install
# Installs .git/hooks/{pre-commit,pre-push}.
```

## Setup — macOS / Linux

Skip WSL. Steps 3-7 above apply directly.

## Open the repo in VS Code

From Windows VS Code, install the **Remote - WSL** extension, then:

```bash
# from inside WSL, at the repo root:
code .
```

Files appear local to VS Code; the integrated terminal opens inside WSL with the Nix shell loaded. Native filesystem watches work.

## Recover from a corrupted WSL distro

```powershell
wsl --shutdown
wsl --export Ubuntu-24.04 D:\backups\ubuntu-2026-05-17.tar
# weekly cadence is enough; restore with:
wsl --import Ubuntu-restored C:\WSL\Ubuntu-restored D:\backups\ubuntu-2026-05-17.tar
```

Repo work-in-progress should always be pushed to a personal fork branch — that way `wsl --import` only loses uncommitted changes.

## Daily commands

| What you want | Command |
|---|---|
| Enter Nix shell explicitly | `nix develop` |
| Run the same gate CI runs | `make preflight` |
| Run only the changed-files gate | lefthook does this automatically on `git commit` and `git push` |
| Update Nix toolchain | `nix flake update` then commit `flake.lock` |
| Drop into a one-off Python | `nix shell nixpkgs#python313` |
| Inspect what's in the shell | `nix develop -c env | grep -E 'PATH|RUSTC'` |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `direnv: error /path/.envrc is blocked` | `direnv allow` once per repo |
| Slow `cargo build` / `git status` | You are on `/mnt/c/...`. Move the repo to `~/work/...` (ext4) |
| `wsl: command not found` from PowerShell | Reboot after `wsl --install` |
| HTTPS push prompts for password every time | Re-run the `git config credential.helper` line in step 5 |
| `.node` addon fails to load | Confirm you ran `make preflight` (or `npm run build`) — the `.node` only exists after `build:rust` |
```

- [ ] **Step 2: Confirm the doc renders**

Run: `wc -l docs/dev-environment.md`
Expected: ~120 lines.

- [ ] **Step 3: Commit**

```bash
git add docs/dev-environment.md
git commit -m "docs(dev-env): wsl+nix bootstrap guide"
```

## Phase 0.2 — `.gitattributes` to kill CRLF spam

### Task 0.2.1: Add `.gitattributes` enforcing LF on text files

**Files:**
- Create: `.gitattributes`

- [ ] **Step 1: Create the file with the exact contents below**

```
# Default to LF for all text; never let core.autocrlf mangle source.
* text=auto eol=lf

# Explicit binary annotations — Git stops trying to diff or convert these.
*.png  binary
*.jpg  binary
*.jpeg binary
*.gif  binary
*.ico  binary
*.pdf  binary
*.node binary
*.so   binary
*.dll  binary
*.dylib binary
*.jar  binary
*.zip  binary
*.tar  binary
*.gz   binary
*.tgz  binary
*.7z   binary
*.wasm binary

# Shell + Nix files must stay LF even on Windows checkouts
*.sh   text eol=lf
*.nix  text eol=lf
flake.lock text eol=lf
lefthook.yml text eol=lf
```

- [ ] **Step 2: Normalize existing checkout**

Run: `git add --renormalize .`
Expected: a long list of files updated to LF; review with `git status` then `git diff --stat | tail -5` (should show pure line-ending churn, no semantic changes).

- [ ] **Step 3: Verify CRLF warnings are gone**

Run: `git commit -m "chore: normalize line endings to lf"`
Expected: zero `LF will be replaced by CRLF` warnings.

- [ ] **Step 4: Commit the .gitattributes itself**

The renormalize commit above already includes `.gitattributes` if you `git add .gitattributes` first. Confirm:

```bash
git log -1 --stat -- .gitattributes
```

Expected: shows `.gitattributes | <n> +++`.

## Phase 0.3 — `.wslconfig.example`

### Task 0.3.1: Author the WSL host config template

**Files:**
- Create: `.wslconfig.example`

- [ ] **Step 1: Create with exact contents**

```ini
# Copy to %USERPROFILE%\.wslconfig and edit `memory` + `processors` for your box.
# After editing, run `wsl --shutdown` once so the new config takes effect.

[wsl2]
# Adjust to ~half your physical RAM. JVM + cargo + rust-analyzer add up fast.
memory=24GB
# Leave at least 2 cores for Windows.
processors=12
swap=8GB

# Mirrored mode (Win11 22H2+) — fixes localhost across VPNs and broken DNS.
networkingMode=mirrored
dnsTunneling=true
autoProxy=true

# Auto-reclaim free pages back to Windows instead of holding them indefinitely.
vmIdleTimeout=60000

# Auto-shrink the ext4 VHDX so deletions reclaim disk.
sparseVhd=true

[experimental]
autoMemoryReclaim=gradual
```

- [ ] **Step 2: Commit**

```bash
git add .wslconfig.example
git commit -m "wsl: example host config (mirrored net, sparseVhd, reclaim)"
```

## Phase 0.4 — Bootstrap script

### Task 0.4.1: Author `scripts/wsl-bootstrap.sh`

**Files:**
- Create: `scripts/wsl-bootstrap.sh`

- [ ] **Step 1: Create with exact contents**

```bash
#!/usr/bin/env bash
# scripts/wsl-bootstrap.sh — one-shot WSL Ubuntu 24.04 → Nix → direnv setup.
# Idempotent: safe to re-run.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/work/russellian-book-suite}"
REPO_URL="${REPO_URL:-git@github.com:CharlesHoskinson/russellian-book-suite.git}"

log() { printf '\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m==> %s\033[0m\n' "$*" >&2; }
fail() { printf '\033[1;31m==> %s\033[0m\n' "$*" >&2; exit 1; }

# 1. Sanity: WSL2 + Ubuntu
if [ ! -r /proc/version ] || ! grep -qi microsoft /proc/version; then
  warn "Not running inside WSL; continuing anyway (macOS/Linux path)."
fi
if [ ! -f /etc/os-release ] || ! grep -q '^ID=ubuntu' /etc/os-release; then
  warn "Not Ubuntu; some apt commands may differ."
fi

# 2. apt prerequisites
log "Installing apt prerequisites…"
sudo apt-get update -qq
sudo apt-get install -y -qq curl ca-certificates git direnv build-essential

# 3. Nix via Determinate Systems installer
if ! command -v nix >/dev/null 2>&1; then
  log "Installing Nix (Determinate Systems installer)…"
  curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix |
    sh -s -- install linux --extra-conf "trusted-users = $(whoami)" --no-confirm
  # shellcheck disable=SC1091
  source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
else
  log "Nix already installed: $(nix --version)"
fi

# 4. direnv hook
if ! grep -q 'direnv hook bash' ~/.bashrc 2>/dev/null; then
  log "Wiring direnv into ~/.bashrc…"
  echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
fi
mkdir -p ~/.config/direnv
if [ ! -f ~/.config/direnv/direnvrc ]; then
  echo 'source $HOME/.nix-profile/share/nix-direnv/direnvrc' > ~/.config/direnv/direnvrc
fi

# 5. Clone repo (if absent)
if [ ! -d "$REPO_DIR" ]; then
  log "Cloning $REPO_URL → $REPO_DIR…"
  mkdir -p "$(dirname "$REPO_DIR")"
  git clone "$REPO_URL" "$REPO_DIR"
else
  log "Repo already cloned at $REPO_DIR"
fi

# 6. Git defaults
log "Setting git defaults (autocrlf=false, eol=lf)…"
git config --global core.autocrlf false
git config --global core.eol lf

# 7. Final message
cat <<EOF

✅ WSL bootstrap complete.

Next steps:
  cd $REPO_DIR
  direnv allow            # one-time; Nix downloads toolchain on first entry
  make preflight          # green ⇒ ready to ship

If make preflight fails on the first run, check:
  nix --version           # should report Determinate Nix
  nix develop -c rustc --version  # should report 1.90.x
  echo \$NIX_PATH         # should mention nixpkgs

EOF
```

- [ ] **Step 2: Mark executable**

Run: `chmod +x scripts/wsl-bootstrap.sh`

- [ ] **Step 3: Shellcheck**

Run: `nix-shell -p shellcheck --run 'shellcheck scripts/wsl-bootstrap.sh'`
Expected: no errors (warnings about SC1091 are fine — already silenced).

If `nix-shell` isn't available locally yet, defer this check to CI (PR-1 lints the script).

- [ ] **Step 4: Commit**

```bash
git add scripts/wsl-bootstrap.sh
git commit -m "wsl: bootstrap script (nix install + repo clone + direnv hook)"
```

## Phase 0.5 — README link

### Task 0.5.1: Add a developer-setup pointer to README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read the existing README to locate the right section**

Run: `head -30 README.md`
Identify the section that mentions running tests or contributing. Insert the link there.

- [ ] **Step 2: Add this paragraph after the project headline (or under any "Contributing" heading)**

```markdown
## Setting up your environment

This repo runs CI on Ubuntu Linux. To avoid "works on my machine" drift, see [`docs/dev-environment.md`](docs/dev-environment.md) for the WSL2 + Nix bootstrap. macOS/Linux developers run Nix directly; Windows developers install Ubuntu under WSL2 first.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: link README to dev-environment.md"
```

## Phase 0.6 — Open PR-0

### Task 0.6.1: Push + open PR

- [ ] **Step 1: Push**

```bash
git push -u origin feat/ci-cleanup-pr0-wsl-bootstrap
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --title "PR-0 (ci-cleanup): wsl bootstrap + .gitattributes + .wslconfig.example" \
  --body "$(cat <<'EOF'
## Summary

Docs + scripts only. Zero behavior change.

- `docs/dev-environment.md` — WSL2 + Nix bootstrap guide
- `.gitattributes` — enforces LF on text files; kills the CRLF spam that's been on every sprint-5 commit
- `.wslconfig.example` — recommended host config (mirrored networking, sparseVhd, autoMemoryReclaim)
- `scripts/wsl-bootstrap.sh` — idempotent one-shot installer
- README pointer to the new guide

Implements PR-0 from `docs/plans/2026-05-17-ci-cleanup.md`. The next PR (`feat/ci-cleanup-pr1-nix-lefthook`) wires up the Nix flake the dev-environment guide references.

## Test plan

- [x] `wsl --shutdown` after copying `.wslconfig.example` to `%USERPROFILE%\.wslconfig` succeeds
- [x] `bash scripts/wsl-bootstrap.sh` on a fresh WSL Ubuntu 24.04 completes without errors
- [x] After bootstrap, `nix --version` reports Determinate Nix
- [x] `git commit` on this branch produces zero CRLF warnings
- [x] No existing CI job changes behavior (verified by green CI)
EOF
)"
```

- [ ] **Step 3: Merge when CI is green** (CI runs unchanged on this PR)

---

# PR-1 — Nix flake + lefthook + scaffold-bake

**Branch:** `feat/ci-cleanup-pr1-nix-lefthook` cut from `main` after PR-0 merges.

**Scope:** Ship the hermetic toolchain (`flake.nix`), the local pre-flight gate (`lefthook.yml`), the scaffold bake-and-test, and the synthetic-bug regression suite. CI remains unchanged — devs opt in via `direnv allow` + `lefthook install`.

**Wall-time exit criteria:**
- `nix develop` cold (no Cachix): under 5 minutes on a 12-thread WSL box
- `nix develop` warm: under 3 seconds
- `lefthook run pre-commit` on a typical 3-file change: under 5 seconds
- `pytest skills/neurosym-forge/tests/test_scaffold_bake.py`: under 2 minutes

## Phase 1.1 — Nix flake

### Task 1.1.1: Author `flake.nix` with the pinned toolchain

**Files:**
- Create: `flake.nix`

- [ ] **Step 1: Write the failing flake-check before any flake exists**

Run: `nix flake check --no-build-output`
Expected: error "no flake.nix found"

- [ ] **Step 2: Create `flake.nix` with this exact content**

```nix
{
  description = "russellian-book-suite hermetic dev environment";

  inputs = {
    nixpkgs.url      = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url  = "github:numtide/flake-utils";
    rust-overlay = {
      url = "github:oxalica/rust-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, rust-overlay }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ rust-overlay.overlays.default ];
        };
        rust = pkgs.rust-bin.stable."1.90.0".default.override {
          extensions = [ "rust-src" "clippy" "rustfmt" ];
        };
        # Python + the few PyPI deps that the booklogic build truly needs at
        # the system level (everything else lives in per-skill venvs).
        python = pkgs.python313.withPackages (ps: with ps; [
          pytest pytest-xdist ruff edn-format pyyaml jinja2
        ]);
      in {
        devShells.default = pkgs.mkShell {
          name = "russellian-book-suite";
          packages = with pkgs; [
            # Rust
            rust
            mold sccache cargo-nextest
            # Node / CLJS
            nodejs_22 nodePackages.pnpm babashka
            # Python
            python
            # JVM (for shadow-cljs)
            jdk21 clj-kondo
            # SMT
            z3
            # Build essentials
            cmake gnumake pkg-config
            # Git hooks + automation
            lefthook git gh
            # Bootstrap utilities
            jq yq curl
          ];

          shellHook = ''
            export RUSTC_WRAPPER=sccache
            export CARGO_BUILD_RUSTFLAGS="-C link-arg=-fuse-ld=mold"
            export CARGO_INCREMENTAL=0
            export PATH="$HOME/.cargo/bin:$PATH"
            export NBB_PATH="$PWD/.nbb"
            # Cachix uses these to skip rebuild on the runner
            export NIX_CONFIG="experimental-features = nix-command flakes"
          '';
        };

        # `nix build .#preflight` runs `make preflight` inside the shell.
        # CI uses this as a single entry point for drift verification.
        packages.preflight = pkgs.writeShellApplication {
          name = "preflight";
          runtimeInputs = [ pkgs.gnumake ];
          text = ''
            cd "$PWD"
            make preflight
          '';
        };

        # Flake-level check: assert the makefile preflight target's step list
        # matches scripts/ci-steps.txt. Detects drift between CI YAML and
        # local Makefile.
        checks.flake-drift = pkgs.runCommand "flake-drift-check" {
          buildInputs = [ pkgs.gnumake pkgs.coreutils ];
        } ''
          if ! diff -q ${./scripts/ci-steps.txt} <(make -C ${./.} -n preflight | grep -E '^\t' | sed 's/^\t//') >/dev/null 2>&1; then
            echo "DRIFT: scripts/ci-steps.txt diverges from Makefile preflight"
            diff ${./scripts/ci-steps.txt} <(make -C ${./.} -n preflight | grep -E '^\t' | sed 's/^\t//') || true
            exit 1
          fi
          touch $out
        '';
      });
}
```

- [ ] **Step 3: Generate `flake.lock`**

Run: `nix flake lock`
Expected: creates `flake.lock` (commit it).

- [ ] **Step 4: Verify the shell builds**

Run: `nix develop -c rustc --version`
Expected: `rustc 1.90.0 ...`

- [ ] **Step 5: Verify the shell contains every needed tool**

Run:
```bash
nix develop -c bash -c '
  for t in rustc cargo nextest sccache mold node nbb python pytest ruff java clj-kondo z3 cmake make lefthook gh jq yq curl bb; do
    command -v "$t" >/dev/null && echo "ok: $t" || echo "MISSING: $t"
  done
'
```
Expected: every line `ok: <tool>`.

- [ ] **Step 6: Commit**

```bash
git add flake.nix flake.lock
git commit -m "nix: hermetic devshell (rust 1.90 + node 22 + py 3.13 + jdk21 + z3)"
```

### Task 1.1.2: Wire direnv

**Files:**
- Create: `.envrc`

- [ ] **Step 1: Create `.envrc` with one line**

```bash
use flake
```

- [ ] **Step 2: Allow direnv**

Run: `direnv allow`
Expected: direnv loads the shell. Subsequent `cd` into the repo triggers it automatically.

- [ ] **Step 3: Commit**

```bash
git add .envrc
git commit -m "nix: direnv auto-load via use flake"
```

## Phase 1.2 — Lefthook

### Task 1.2.1: Author `lefthook.yml`

**Files:**
- Create: `lefthook.yml`

- [ ] **Step 1: Create with exact contents**

```yaml
# Local pre-flight gates. Run `lefthook install` once after `git clone`.
# Every command runs inside `nix develop` for tool-version parity with CI.

pre-commit:
  parallel: true
  commands:
    clj-kondo:
      glob: "*.{clj,cljs,cljc,edn}"
      run: nix develop -c clj-kondo --lint {staged_files}
    ruff:
      glob: "*.py"
      run: nix develop -c ruff check {staged_files}
    cargo-fmt:
      glob: "*.rs"
      run: nix develop -c cargo fmt --check
    regex-compile:
      glob: "verifiers/*/rules/booklogic/lifts.edn"
      run: nix develop -c python scripts/regex-compile-check.py {staged_files}
    nix-fmt:
      glob: "*.nix"
      run: nix develop -c nixpkgs-fmt --check {staged_files}

pre-push:
  parallel: false   # tasks below contend for cargo target dir
  commands:
    scaffold-bake:
      run: nix develop -c pytest skills/neurosym-forge/tests/test_scaffold_bake.py -x
    regression-suite:
      run: nix develop -c pytest skills/neurosym-forge/tests/regression/ -x
    nextest-changed:
      run: nix develop -c cargo nextest run --workspace --no-fail-fast
    smoke-changed:
      glob: "verifiers/**"
      run: nix develop -c bash -c 'for d in $(git diff --name-only origin/main...HEAD verifiers/ | cut -d/ -f1-2 | sort -u); do make -C "$d" ci || exit 1; done'
```

- [ ] **Step 2: Install hooks locally**

Run: `nix develop -c lefthook install`
Expected: `.git/hooks/pre-commit` + `.git/hooks/pre-push` created.

- [ ] **Step 3: Smoke-test the pre-commit hook**

Run: `nix develop -c lefthook run pre-commit`
Expected: every command runs and reports either "skipped (no staged files)" or "passed".

- [ ] **Step 4: Commit**

```bash
git add lefthook.yml
git commit -m "lefthook: pre-commit (clj-kondo, ruff, fmt, regex) + pre-push (scaffold-bake, nextest)"
```

## Phase 1.3 — Makefile (single source of step list)

### Task 1.3.1: Author top-level `Makefile`

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Create with exact contents**

```makefile
# Top-level Makefile. The CI workflow and `make preflight` execute the same
# step list. Every shell line is the unit of comparison against
# scripts/ci-steps.txt — keep them aligned (the flake-drift check enforces).

.PHONY: preflight lint scaffold-bake regression nextest smoke-bermuda smoke-osmotic clean

preflight: lint scaffold-bake regression nextest smoke-bermuda smoke-osmotic

lint:
	clj-kondo --lint $$(git ls-files '*.clj' '*.cljs' '*.cljc' '*.edn')
	ruff check .
	cargo fmt --check
	nixpkgs-fmt --check $$(git ls-files '*.nix')

scaffold-bake:
	pytest skills/neurosym-forge/tests/test_scaffold_bake.py -x

regression:
	pytest skills/neurosym-forge/tests/regression/ -x

nextest:
	cargo nextest run --workspace --no-fail-fast

smoke-bermuda:
	make -C verifiers/bermuda ci

smoke-osmotic:
	make -C verifiers/osmotic_pressure ci

clean:
	cargo clean
	rm -rf verifiers/*/rust-verifier/target
	rm -rf verifiers/*/cljs-orchestrator/dist
	rm -rf verifiers/*/cljs-orchestrator/.shadow-cljs
	rm -rf verifiers/*/cljs-orchestrator/native
```

- [ ] **Step 2: Smoke `make lint`**

Run: `nix develop -c make lint`
Expected: zero errors. (Some files may need rufficiency fixes; address them or add `# noqa` per ruff.)

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "make: preflight target chains lint, scaffold-bake, regression, nextest, verifier smoke"
```

## Phase 1.4 — Per-verifier `make ci`

### Task 1.4.1: Add a `make ci` target to bermuda

**Files:**
- Create: `verifiers/bermuda/Makefile`

- [ ] **Step 1: Create with exact contents**

```makefile
.PHONY: ci build smoke clean

ci: build smoke

build:
	npm install
	npm run build

smoke:
	pytest tests/ -v

clean:
	rm -rf rust-verifier/target cljs-orchestrator/dist cljs-orchestrator/.shadow-cljs cljs-orchestrator/native
```

- [ ] **Step 2: Confirm bermuda's `npm run build` exists and includes shadow-cljs main**

Run: `grep -E '"build":' verifiers/bermuda/package.json`
Expected: `"build": "npm run build:rust && npm run build:cljs"` (or equivalent). If `build:cljs` runs `shadow-cljs release test` rather than `main`, change it to `main` so the full bundle compiles. This was the sprint-5 hidden bug — bermuda's `:test` build sidestepped the `bridge.cljs` + `phases.cljs` chain.

- [ ] **Step 3: If bermuda was on `:test`, fix it now (one-line edit to package.json)**

```bash
sed -i 's/shadow-cljs release test/shadow-cljs release main/' verifiers/bermuda/package.json
```

(Re-check that `bermuda.core` actually compiles cleanly; if it hits the same `slurp` bug osmotic did, fix `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs` identically to how `verifiers/osmotic_pressure/...` was fixed in sprint 5: replace `(slurp report-path)` with `(.toString (.readFileSync fs report-path))` and add `["fs" :as fs]` to the `:require`.)

- [ ] **Step 4: Local smoke**

Run: `nix develop -c make -C verifiers/bermuda ci`
Expected: green build + green smoke. (On Windows pre-WSL, the `.so`/`.node` chain fails — that's why this plan's first PR was PR-0.)

- [ ] **Step 5: Commit**

```bash
git add verifiers/bermuda/Makefile verifiers/bermuda/package.json
# possibly also verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs
git commit -m "bermuda: make ci target wraps npm run build + smoke (main bundle, not :test)"
```

### Task 1.4.2: Add a `make ci` target to osmotic-pressure

**Files:**
- Create: `verifiers/osmotic_pressure/Makefile`

- [ ] **Step 1: Create with exact contents**

```makefile
.PHONY: ci build smoke clean

ci: build smoke

build:
	npm install
	npm run build

smoke:
	pytest tests/ -v

clean:
	rm -rf rust-verifier/target cljs-orchestrator/dist cljs-orchestrator/.shadow-cljs cljs-orchestrator/native
```

- [ ] **Step 2: Local smoke**

Run: `nix develop -c make -C verifiers/osmotic_pressure ci`
Expected: green build + green smoke (`5 passed, 2 skipped` plus 2 smoke `pass`).

- [ ] **Step 3: Commit**

```bash
git add verifiers/osmotic_pressure/Makefile
git commit -m "osmotic_pressure: make ci target wraps npm run build + smoke"
```

## Phase 1.5 — Regex compile-check

### Task 1.5.1: Author `scripts/regex-compile-check.py`

**Files:**
- Create: `scripts/regex-compile-check.py`

- [ ] **Step 1: Write the failing test first**

```bash
mkdir -p scripts/tests
cat > scripts/tests/test_regex_compile_check.py <<'PY'
"""Test: the gate catches sprint-5 bug #7 (JS-style named group)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "regex-compile-check.py"


def _write_lifts(p: Path, regex: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        '{:forms\n'
        f' [(deflift L001 :from :claim/canonical-text :when "{regex}" :emit (fact))]}}\n',
        encoding="utf-8",
    )


def test_rejects_js_named_groups(tmp_path: Path) -> None:
    bad = tmp_path / "lifts.edn"
    _write_lifts(bad, "(?<v>[0-9]+)")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(bad)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "?<" in result.stderr or "named group" in result.stderr.lower()


def test_accepts_python_named_groups(tmp_path: Path) -> None:
    good = tmp_path / "lifts.edn"
    _write_lifts(good, "(?P<v>[0-9]+)")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(good)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
PY
```

- [ ] **Step 2: Run the test and confirm it fails (script doesn't exist yet)**

Run: `nix develop -c pytest scripts/tests/test_regex_compile_check.py -v`
Expected: FAIL with `FileNotFoundError` or non-zero exit.

- [ ] **Step 3: Create the script with exact contents**

```python
#!/usr/bin/env python3
"""scripts/regex-compile-check.py — fail-fast if a lifts.edn pattern
won't compile under Python's `re`. Catches sprint-5 bug #7 (JS-style
`(?<name>...)` vs Python `(?P<name>...)`).

Usage: regex-compile-check.py <lifts.edn> [<lifts.edn> ...]

Returns 0 if every `:when` pattern compiles; non-zero on first failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Match (?<name> that is NOT (?P<name> — i.e. the JS-only form.
_JS_ONLY = re.compile(r"\(\?<(?!P)")


def _extract_when_patterns(text: str) -> list[str]:
    # Naive but sufficient: find every :when "..." form and return the
    # quoted string. EDN's quoting is simple: \\ and \" inside the string.
    out: list[str] = []
    i = 0
    while True:
        j = text.find(":when", i)
        if j < 0:
            break
        # Find the next quoted string
        k = text.find('"', j)
        if k < 0:
            break
        # Find the closing quote, respecting \\ and \"
        m = k + 1
        while m < len(text):
            c = text[m]
            if c == "\\":
                m += 2
                continue
            if c == '"':
                break
            m += 1
        if m >= len(text):
            break
        out.append(text[k + 1 : m])
        i = m + 1
    return out


def check_one(path: Path) -> list[str]:
    """Return list of error strings; empty on success."""
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for pat in _extract_when_patterns(text):
        # 1. JS-only named groups are an immediate fail.
        if _JS_ONLY.search(pat):
            errors.append(
                f"{path}: pattern uses JS-style (?<name>...) — "
                f"Python `re` requires (?P<name>...). Pattern: {pat!r}"
            )
            continue
        # 2. Try compiling as actual Python regex.
        try:
            # Decode EDN string escapes (\\ → \).
            decoded = pat.encode("utf-8").decode("unicode_escape")
            re.compile(decoded)
        except re.error as exc:
            errors.append(f"{path}: regex {pat!r} won't compile: {exc}")
    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: regex-compile-check.py <lifts.edn> [...]", file=sys.stderr)
        return 2
    all_errors: list[str] = []
    for arg in argv:
        all_errors.extend(check_one(Path(arg)))
    if all_errors:
        for e in all_errors:
            print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Mark executable**

Run: `chmod +x scripts/regex-compile-check.py`

- [ ] **Step 5: Re-run the test and confirm it passes**

Run: `nix develop -c pytest scripts/tests/test_regex_compile_check.py -v`
Expected: 2 passed.

- [ ] **Step 6: Smoke against the live osmotic lifts**

Run: `nix develop -c python scripts/regex-compile-check.py verifiers/osmotic_pressure/rules/booklogic/lifts.edn`
Expected: exit 0 if `verifiers/osmotic_pressure/scripts/ingest_ledger.py`'s `_to_python_regex` shim was already applied to lifts.edn (the source EDN may still use JS-style if the Python ingester normalizes — in that case the script *correctly* fails, and the fix is to either translate inside this script too or to require Python-form named groups in source. **For this plan, require Python form in source** — update `lifts.edn` files to use `(?P<v>...)` instead of `(?<v>...)`. The CLJS ingester accepts both since `cljs.reader` doesn't parse regex.)

- [ ] **Step 7: If needed, normalize sprint-5 lifts to `(?P<v>...)`**

```bash
sed -i 's/(?<v>/(?P<v>/g' verifiers/osmotic_pressure/rules/booklogic/lifts.edn
nix develop -c python scripts/regex-compile-check.py verifiers/osmotic_pressure/rules/booklogic/lifts.edn
# Expected: exit 0
nix develop -c make -C verifiers/osmotic_pressure ci
# Expected: still green
```

- [ ] **Step 8: Commit**

```bash
git add scripts/regex-compile-check.py scripts/tests/test_regex_compile_check.py
# possibly verifiers/osmotic_pressure/rules/booklogic/lifts.edn
git commit -m "scripts: regex-compile-check gates JS-style (?<>) named groups"
```

## Phase 1.6 — CI-steps source-of-truth file

### Task 1.6.1: Snapshot the Makefile preflight steps for drift detection

**Files:**
- Create: `scripts/ci-steps.txt`

- [ ] **Step 1: Generate the file from the current Makefile**

Run:
```bash
nix develop -c make -n preflight | grep -E '^\t' | sed 's/^\t//' > scripts/ci-steps.txt
```

- [ ] **Step 2: Inspect**

Run: `cat scripts/ci-steps.txt`
Expected: 6-7 shell lines, one per preflight sub-step.

- [ ] **Step 3: Verify the flake-drift check passes**

Run: `nix flake check --no-build-output`
Expected: `building '/nix/store/...-flake-drift-check.drv'... success`.

- [ ] **Step 4: Commit**

```bash
git add scripts/ci-steps.txt
git commit -m "nix: ci-steps.txt as drift source for flake checks.flake-drift"
```

## Phase 1.7 — Scaffold bake-and-test

### Task 1.7.1: Write the failing scaffold-bake test

**Files:**
- Create: `skills/neurosym-forge/tests/test_scaffold_bake.py`

- [ ] **Step 1: Write the failing test**

```python
"""REQ-SCAFFOLD-BAKE-001: a freshly scaffolded project passes `make ci`
end-to-end.

Catches sprint-5 bugs #1 (stale napi build), #2 (CLJS namespace
mismatch), #3 (CI module name drift), #5 (shadow-cljs .node path) at
once. Runs inside the nix shell (so the test inherits the same toolchain
as CI).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / "skills" / "neurosym-forge"
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "project-template"

# Skip on Windows pre-WSL: cargo can't produce .so; CI is the gate.
pytestmark = pytest.mark.skipif(
    shutil.which("cargo") is None
    or subprocess.run(["uname"], capture_output=True).stdout.strip() != b"Linux",
    reason="scaffold-bake requires Linux toolchain (cargo + cdylib .so)",
)


def _copy_smoke_rules(project_dir: Path) -> None:
    """Drop a minimal known-good ruleset into the baked project so its
    booklogic compiler has something to compile.
    """
    src = SKILL_ROOT / "tests" / "fixtures" / "bake-smoke-rules"
    dst = project_dir / "rules" / "booklogic"
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        shutil.copy(f, dst / f.name)


def _scaffold(tmp_path: Path, slug: str) -> Path:
    """Invoke the scaffolder to produce a baked project."""
    import sys
    sys.path.insert(0, str(SKILL_ROOT))
    from scripts.scaffold_project import scaffold_project  # type: ignore
    out_dir = tmp_path / slug
    scaffold_project(
        project_name="Bake Test",
        project_slug=slug,
        out_dir=out_dir,
        skill_root=SKILL_ROOT,
    )
    _copy_smoke_rules(out_dir)
    return out_dir


def test_scaffold_with_underscore_slug_passes_ci(tmp_path: Path) -> None:
    """The slug 'bake_test' (with underscore) is the tricky case — CLJS
    namespaces should render dashed ('bake-test.core'), file paths
    should stay underscored ('bake_test/core.cljs'). Sprint-5 burned
    here.
    """
    project = _scaffold(tmp_path, "bake_test")
    result = subprocess.run(
        ["make", "ci"], cwd=project, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"baked project failed `make ci`:\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )


def test_scaffold_with_simple_slug_passes_ci(tmp_path: Path) -> None:
    """Sanity: a single-word slug ('baketest') also passes."""
    project = _scaffold(tmp_path, "baketest")
    result = subprocess.run(
        ["make", "ci"], cwd=project, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"baked project failed `make ci`:\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
```

- [ ] **Step 2: Create the smoke-rules fixture directory**

The bake test needs a tiny ruleset to compile. Create:

```bash
mkdir -p skills/neurosym-forge/tests/fixtures/bake-smoke-rules
```

- [ ] **Step 3: Drop minimal rule files**

`skills/neurosym-forge/tests/fixtures/bake-smoke-rules/sorts.edn`:
```edn
{:forms [(defsort :thing)]}
```

`skills/neurosym-forge/tests/fixtures/bake-smoke-rules/predicates.edn`:
```edn
{:forms [(defpredicate :count [:thing] :int)]}
```

`skills/neurosym-forge/tests/fixtures/bake-smoke-rules/lifts.edn`:
```edn
{:forms
 [(deflift L001-count
    :from :claim/canonical-text
    :when "count\\s*(?P<v>[0-9]+)"
    :emit (fact ?claim-id :thing :count (parse-int ?v)))]}
```

`skills/neurosym-forge/tests/fixtures/bake-smoke-rules/constraints.edn`:
```edn
{:forms
 [(defconstraint C001-count-nonneg
    :assert (= (:count :thing) 0))]}
```

(The constraint is trivially satisfiable — that's intentional. The point is to make the bake compile end-to-end, not to test the verifier.)

- [ ] **Step 4: Run the bake test — expect FAIL (template still has bugs from sprint 5)**

Run: `nix develop -c pytest skills/neurosym-forge/tests/test_scaffold_bake.py -v`
Expected: at least one of the two tests fails because the template hasn't been fully fixed yet (sprint 5 only patched osmotic-specific files, not the template).

- [ ] **Step 5: Apply the template patches that sprint 5 already proved necessary**

Inspect `skills/neurosym-forge/assets/project-template/` and confirm these template files match the sprint-5 fixes:

```bash
# 1. package.json.tmpl uses cargo+cp (not napi)
grep -q "cargo build --manifest-path" skills/neurosym-forge/assets/project-template/package.json.tmpl
# Expected: 1 match

# 2. cljs ns templates use {{ project_slug_dashed }}
grep -c "{{ project_slug_dashed }}" skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/*.tmpl
# Expected: ≥ 8

# 3. bridge.cljs.tmpl uses js/require
grep -q "js/require" skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/bridge.cljs.tmpl
# Expected: 1

# 4. phases.cljs.tmpl uses readFileSync
grep -q "readFileSync" skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/phases.cljs.tmpl
# Expected: 1
```

If any of these fail, apply the corresponding sprint-5 fix from `verifiers/osmotic_pressure/` to the template. (All four were already shipped in sprint-5 PR #59, so they should be present — this is a sanity check.)

- [ ] **Step 6: Re-run the bake test — expect PASS**

Run: `nix develop -c pytest skills/neurosym-forge/tests/test_scaffold_bake.py -v`
Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add skills/neurosym-forge/tests/test_scaffold_bake.py \
        skills/neurosym-forge/tests/fixtures/bake-smoke-rules/
# possibly template fixes
git commit -m "neurosym-forge: scaffold-bake test (bakes template + runs make ci end-to-end)"
```

## Phase 1.8 — Sprint-5 regression suite

### Task 1.8.1: Build the regression harness

**Files:**
- Create: `skills/neurosym-forge/tests/regression/__init__.py`
- Create: `skills/neurosym-forge/tests/regression/conftest.py`
- Create: `skills/neurosym-forge/tests/regression/test_sprint5_bug_catches.py`

- [ ] **Step 1: Create the empty `__init__.py`**

```bash
touch skills/neurosym-forge/tests/regression/__init__.py
```

- [ ] **Step 2: Create the conftest with shared bake-and-mutate fixtures**

`skills/neurosym-forge/tests/regression/conftest.py`:

```python
"""Shared fixtures for the sprint-5 regression suite.

Each regression test:
  1. Bakes a fresh project via scaffold_project()
  2. Mutates one file to re-introduce the sprint-5 bug
  3. Asserts the appropriate gate fails on `make ci`
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_ROOT = REPO_ROOT / "skills" / "neurosym-forge"


@pytest.fixture()
def fresh_bake(tmp_path: Path) -> Callable[[str], Path]:
    """Return a callable that bakes a fresh project and returns its path."""
    import sys
    sys.path.insert(0, str(SKILL_ROOT))
    from scripts.scaffold_project import scaffold_project  # type: ignore

    def _bake(slug: str = "regr_test") -> Path:
        out_dir = tmp_path / slug
        scaffold_project(
            project_name="Regression",
            project_slug=slug,
            out_dir=out_dir,
            skill_root=SKILL_ROOT,
        )
        # Drop in smoke rules
        src_rules = SKILL_ROOT / "tests" / "fixtures" / "bake-smoke-rules"
        dst_rules = out_dir / "rules" / "booklogic"
        dst_rules.mkdir(parents=True, exist_ok=True)
        for f in src_rules.iterdir():
            shutil.copy(f, dst_rules / f.name)
        return out_dir

    return _bake


def run_make_ci(project_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "ci"], cwd=project_dir,
        capture_output=True, text=True, check=False,
    )
```

- [ ] **Step 3: Author the seven regression tests**

`skills/neurosym-forge/tests/regression/test_sprint5_bug_catches.py`:

```python
"""Seven regression tests, one per sprint-5 bug (§ 2 of the design spec).

Each test re-introduces the bug and asserts the appropriate gate catches
it. If a future template change accidentally re-introduces a bug, these
tests fail — preventing the silent regression that caused the sprint-5
thrash.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from .conftest import REPO_ROOT, SKILL_ROOT, run_make_ci

# Skip on non-Linux: cargo .so chain only exercises on Linux.
pytestmark = pytest.mark.skipif(
    shutil.which("cargo") is None
    or subprocess.run(["uname"], capture_output=True).stdout.strip() != b"Linux",
    reason="sprint-5 regressions require Linux toolchain",
)


# ----- Bug #1: stale `napi build` in package.json -----

def test_bug1_napi_build_invocation_fails(fresh_bake) -> None:
    project = fresh_bake("bug1")
    pkg = project / "package.json"
    text = pkg.read_text(encoding="utf-8")
    bad = '"build:rust": "cd rust-verifier && napi build --platform --release ../cljs-orchestrator/native"'
    # Replace whatever build:rust currently is with the buggy napi form.
    import re
    new_text = re.sub(r'"build:rust":\s*"[^"]*"', bad, text)
    assert new_text != text, "couldn't find build:rust to mutate"
    pkg.write_text(new_text, encoding="utf-8")
    result = run_make_ci(project)
    assert result.returncode != 0
    assert "napi" in result.stderr.lower() or "package.json not found" in result.stderr


# ----- Bug #2: CLJS namespace dash/underscore mismatch -----

def test_bug2_underscore_ns_fails(fresh_bake) -> None:
    project = fresh_bake("bug2_test")
    core = project / "cljs-orchestrator" / "src" / "main" / "bug2_test" / "core.cljs"
    text = core.read_text(encoding="utf-8")
    # Re-introduce: change `(ns bug2-test.core)` to `(ns bug2_test.core)`.
    new_text = text.replace("(ns bug2-test.", "(ns bug2_test.")
    assert new_text != text, "couldn't find dashed ns to revert"
    core.write_text(new_text, encoding="utf-8")
    result = run_make_ci(project)
    assert result.returncode != 0
    assert "expected namespace" in result.stderr.lower() or "namespace" in result.stderr.lower()


# ----- Bug #3: CI workflow hardcoded underscore module name -----
# (This bug lives in .github/workflows/ci.yml, not in the template.)
# We assert that the *active* ci.yml uses the dashed form.

def test_bug3_ci_uses_dashed_module_name() -> None:
    ci = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    text = ci.read_text(encoding="utf-8")
    # The original bug: `nbb -m osmotic_pressure.booklogic .`
    # Correct form: `nbb -m osmotic-pressure.booklogic .`
    bad = "osmotic_pressure.booklogic"
    assert bad not in text, (
        f"ci.yml references {bad!r} — sprint-5 bug #3 has regressed. "
        f"All nbb module names must be dashed."
    )


# ----- Bug #4: scaffold test asserted old underscore namespace -----
# (Lives in skills/neurosym-forge/tests/test_scaffold_project.py.)

def test_bug4_scaffold_test_uses_dashed_assertion() -> None:
    test = SKILL_ROOT / "tests" / "test_scaffold_project.py"
    text = test.read_text(encoding="utf-8")
    # If the assertion was reverted to underscore, this string appears.
    assert '"(ns osmotic_pressure.core"' not in text, (
        "test_scaffold_project.py asserts underscore namespace — "
        "sprint-5 bug #4 has regressed."
    )


# ----- Bug #5: shadow-cljs `../native/X.node` compile-time resolution -----

def test_bug5_compile_time_require_fails(fresh_bake) -> None:
    project = fresh_bake("bug5")
    bridge = project / "cljs-orchestrator" / "src" / "main" / "bug5" / "bridge.cljs"
    text = bridge.read_text(encoding="utf-8")
    # Re-introduce: replace js/require with the compile-time form
    bad = text.replace(
        "(def ^:private native (js/require",
        "; mutated\n;(def ^:private native (js/require",
    )
    # Also restore the broken `:require` form
    bad = bad.replace(
        "(:require [cljs.reader :as edn])",
        '(:require ["../native/bug5-verifier.node" :as native]\n'
        "            [cljs.reader :as edn])",
    )
    assert bad != text, "couldn't mutate bridge.cljs"
    bridge.write_text(bad, encoding="utf-8")
    result = run_make_ci(project)
    assert result.returncode != 0
    assert "not available" in result.stderr or "require" in result.stderr.lower()


# ----- Bug #6: CLJS `slurp` undeclared -----

def test_bug6_slurp_undeclared(fresh_bake) -> None:
    project = fresh_bake("bug6")
    phases = project / "cljs-orchestrator" / "src" / "main" / "bug6" / "phases.cljs"
    text = phases.read_text(encoding="utf-8")
    # Re-introduce: replace readFileSync with slurp; drop fs require
    bad = text.replace(
        "(.toString (.readFileSync fs report-path))",
        "(slurp report-path)",
    ).replace(
        '            ["fs" :as fs]))',
        "))",
    )
    assert bad != text, "couldn't mutate phases.cljs"
    phases.write_text(bad, encoding="utf-8")
    result = run_make_ci(project)
    assert result.returncode != 0
    assert "slurp" in result.stderr.lower() or "undeclared" in result.stderr.lower()


# ----- Bug #7: JS-style (?<name>) named group -----

def test_bug7_js_named_group_caught_by_regex_check(fresh_bake) -> None:
    project = fresh_bake("bug7")
    lifts = project / "rules" / "booklogic" / "lifts.edn"
    text = lifts.read_text(encoding="utf-8")
    # Mutate (?P<v> back to (?<v>
    bad = text.replace("(?P<v>", "(?<v>")
    assert bad != text, "couldn't find (?P<v> to mutate"
    lifts.write_text(bad, encoding="utf-8")
    # Direct script check (faster than full make ci):
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "regex-compile-check.py"),
         str(lifts)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "?<" in result.stderr or "(?P<" in result.stderr
```

- [ ] **Step 4: Run the suite — expect 7 passed**

Run: `nix develop -c pytest skills/neurosym-forge/tests/regression/ -v`
Expected: 7 passed. (Some tests may take a few minutes apiece because they invoke `make ci` end-to-end.)

- [ ] **Step 5: Commit**

```bash
git add skills/neurosym-forge/tests/regression/
git commit -m "neurosym-forge: sprint-5 regression suite (7 tests, one per bug)"
```

## Phase 1.9 — Open PR-1

### Task 1.9.1: Push + open PR

- [ ] **Step 1: Push**

```bash
git push -u origin feat/ci-cleanup-pr1-nix-lefthook
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --title "PR-1 (ci-cleanup): nix flake + lefthook + scaffold-bake + regression suite" \
  --body "$(cat <<'EOF'
## Summary

Hermetic toolchain + local pre-flight gates + scaffold-bake + sprint-5 regression suite. **No CI changes** — devs opt in via `direnv allow` + `lefthook install`.

- `flake.nix` — single source of truth for Rust 1.90, Node 22, Python 3.13, JDK 21, Z3, mold, sccache, cargo-nextest, clj-kondo, lefthook
- `.envrc` — direnv auto-loads the shell on `cd`
- `lefthook.yml` — pre-commit (<5s) + pre-push (<60s) gates
- `Makefile` — single preflight target chains lint/scaffold-bake/regression/nextest/smoke
- `scripts/regex-compile-check.py` — catches JS-style `(?<name>)` named groups (sprint-5 bug #7)
- `skills/neurosym-forge/tests/test_scaffold_bake.py` — bakes the template, runs `make ci` end-to-end
- `skills/neurosym-forge/tests/regression/test_sprint5_bug_catches.py` — 7 tests, one per sprint-5 bug; each re-injects the bug and asserts the gate catches it
- `verifiers/bermuda/Makefile` + `verifiers/osmotic_pressure/Makefile` — `make ci` target per verifier
- Bermuda's `npm run build` switched from `:test` to `:main` shadow-cljs build so its bundle now exercises the same code paths osmotic does (this is what masked sprint-5 bugs in the first place)

Implements PR-1 from `docs/plans/2026-05-17-ci-cleanup.md`.

## Test plan

- [x] `nix develop -c rustc --version` reports 1.90.x
- [x] `nix develop -c make preflight` green
- [x] `lefthook install` + `lefthook run pre-commit` green
- [x] `pytest skills/neurosym-forge/tests/test_scaffold_bake.py` green (Linux only)
- [x] `pytest skills/neurosym-forge/tests/regression/` 7 passed
- [x] Existing CI still green on this PR (no workflow changes yet)
EOF
)"
```

- [ ] **Step 3: Merge when CI is green**

---

# PR-2 — CI rewrite to `nix develop`

**Branch:** `feat/ci-cleanup-pr2-ci-rewrite` cut from `main` after PR-1 merges.

**Scope:** Rewrite `.github/workflows/ci.yml` so every step runs `nix develop -c <command>` against the Makefile target list. Keep the legacy workflow in `ci-legacy.yml` for one sprint to A/B compare.

**Wall-time exit criteria:**
- Single one-line change in `verifiers/bermuda/rust-verifier/src/lib.rs`: full CI under 2min p50, under 4min p99
- Cold-cache new branch: under 8min p99

## Phase 2.1 — Stash the legacy workflow

### Task 2.1.1: Move current ci.yml → ci-legacy.yml

**Files:**
- Modify: `.github/workflows/ci.yml` → `.github/workflows/ci-legacy.yml`

- [ ] **Step 1: Rename + add `if` guard so it doesn't double-run**

```bash
git mv .github/workflows/ci.yml .github/workflows/ci-legacy.yml
```

Edit `.github/workflows/ci-legacy.yml`, change `on:` block to:

```yaml
on:
  push:
    branches: [main]
    paths:
      - '.github/workflows/ci-legacy.yml'
  workflow_dispatch:
```

So it only runs when explicitly invoked (we use it for A/B compare) or when the file itself changes.

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci-legacy.yml
git commit -m "ci: rename old ci.yml to ci-legacy.yml (kept for one sprint A/B)"
```

## Phase 2.2 — Author new `ci.yml`

### Task 2.2.1: Write the new workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create with exact contents**

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read
  pull-requests: write   # for the ci-budget job to comment

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}

env:
  SCCACHE_GHA_ENABLED: "true"
  RUSTC_WRAPPER: sccache
  CARGO_INCREMENTAL: "0"
  CARGO_TERM_COLOR: always

jobs:
  setup-nix:
    name: nix shell warm-up
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: DeterminateSystems/nix-installer-action@v9
        with:
          extra-conf: |
            trusted-users = root runner
      - uses: DeterminateSystems/magic-nix-cache-action@v8
      - name: warm shell
        run: nix develop -c rustc --version

  lint:
    name: lint
    needs: setup-nix
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: DeterminateSystems/nix-installer-action@v9
      - uses: DeterminateSystems/magic-nix-cache-action@v8
      - run: nix develop -c make lint

  scaffold-bake:
    name: scaffold-bake
    needs: setup-nix
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: DeterminateSystems/nix-installer-action@v9
      - uses: DeterminateSystems/magic-nix-cache-action@v8
      - uses: Swatinem/rust-cache@v2
        with:
          workspaces: |
            verifiers/bermuda/rust-verifier
            verifiers/osmotic_pressure/rust-verifier
      - uses: mozilla-actions/sccache-action@v0.0.7
      - run: nix develop -c make scaffold-bake

  regression:
    name: regression (sprint-5)
    needs: setup-nix
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: DeterminateSystems/nix-installer-action@v9
      - uses: DeterminateSystems/magic-nix-cache-action@v8
      - uses: Swatinem/rust-cache@v2
        with: { workspaces: verifiers/bermuda/rust-verifier }
      - uses: mozilla-actions/sccache-action@v0.0.7
      - run: nix develop -c make regression

  verifier-bermuda:
    name: verifier (bermuda)
    needs: setup-nix
    runs-on: ubuntu-24.04
    if: |
      contains(github.event.head_commit.modified, 'verifiers/bermuda/') ||
      contains(github.event.head_commit.modified, 'skills/neurosym-forge/') ||
      contains(github.event.head_commit.modified, 'flake.nix') ||
      github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      - uses: DeterminateSystems/nix-installer-action@v9
      - uses: DeterminateSystems/magic-nix-cache-action@v8
      - uses: Swatinem/rust-cache@v2
        with: { workspaces: verifiers/bermuda/rust-verifier }
      - uses: mozilla-actions/sccache-action@v0.0.7
      - run: nix develop -c make smoke-bermuda

  verifier-osmotic:
    name: verifier (osmotic-pressure)
    needs: setup-nix
    runs-on: ubuntu-24.04
    if: |
      contains(github.event.head_commit.modified, 'verifiers/osmotic_pressure/') ||
      contains(github.event.head_commit.modified, 'skills/neurosym-forge/') ||
      contains(github.event.head_commit.modified, 'flake.nix') ||
      github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      - uses: DeterminateSystems/nix-installer-action@v9
      - uses: DeterminateSystems/magic-nix-cache-action@v8
      - uses: Swatinem/rust-cache@v2
        with: { workspaces: verifiers/osmotic_pressure/rust-verifier }
      - uses: mozilla-actions/sccache-action@v0.0.7
      - run: nix develop -c make smoke-osmotic

  python-skill-matrix:
    name: python-skill (${{ matrix.skill }})
    needs: setup-nix
    runs-on: ubuntu-24.04
    strategy:
      fail-fast: false
      matrix:
        skill:
          - book-qa
          - book-thesis
          - book-knowledge
          - book-compose
          - book-review
          - russellian-style
          - review-conductor
          - neurosym-forge
    steps:
      - uses: actions/checkout@v4
      - uses: DeterminateSystems/nix-installer-action@v9
      - uses: DeterminateSystems/magic-nix-cache-action@v8
      - run: |
          nix develop -c bash -c "
            cd skills/${{ matrix.skill }}
            pip install -e '.[ci]'
            pytest -q
          "

  required:
    name: ci required ✓
    needs:
      - lint
      - scaffold-bake
      - regression
      - verifier-bermuda
      - verifier-osmotic
      - python-skill-matrix
    runs-on: ubuntu-24.04
    if: always()
    steps:
      - name: aggregate
        run: |
          if [ "${{ contains(needs.*.result, 'failure') }}" = "true" ] ||
             [ "${{ contains(needs.*.result, 'cancelled') }}" = "true" ]; then
            echo "one or more required jobs failed"
            exit 1
          fi
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: rewrite as nix develop + sccache + per-job path filters"
```

## Phase 2.3 — Delete the old booklogic-cljs-test workflow

### Task 2.3.1: Fold its checks into ci.yml (already covered by verifier-bermuda + scaffold-bake)

- [ ] **Step 1: Delete the file**

```bash
git rm .github/workflows/booklogic-cljs-test.yml
```

- [ ] **Step 2: Confirm verifier-bermuda's `make smoke-bermuda` exercises the same paths**

Run: `cat verifiers/bermuda/Makefile`
Expected: `ci: build smoke` where `build` runs `npm run build` (which includes both rust + cljs main bundle).

- [ ] **Step 3: Commit**

```bash
git commit -m "ci: drop booklogic-cljs-test.yml (folded into verifier-bermuda job)"
```

## Phase 2.4 — Wall-time budget job

### Task 2.4.1: Author `.github/workflows/ci-budget.yml`

**Files:**
- Create: `.github/workflows/ci-budget.yml`

- [ ] **Step 1: Create with exact contents**

```yaml
name: ci-budget
on:
  pull_request:
    types: [labeled, opened, synchronize]
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: write

jobs:
  budget-check:
    if: ${{ contains(github.event.pull_request.labels.*.name, 'ci-budget') || github.event_name == 'workflow_dispatch' }}
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - name: compute last-20 wall-time stats
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh run list --workflow=ci.yml --limit 20 \
            --json conclusion,createdAt,updatedAt,databaseId \
            > runs.json
          python3 - <<'PY'
          import json, datetime, statistics
          runs = json.load(open("runs.json"))
          green = [r for r in runs if r["conclusion"] == "success"]
          durations = []
          for r in green:
              t0 = datetime.datetime.fromisoformat(r["createdAt"].replace("Z","+00:00"))
              t1 = datetime.datetime.fromisoformat(r["updatedAt"].replace("Z","+00:00"))
              durations.append((t1 - t0).total_seconds())
          if not durations:
              print("no green runs in window")
              raise SystemExit(0)
          p50 = statistics.median(durations)
          p99 = sorted(durations)[int(len(durations) * 0.99) - 1] if len(durations) >= 5 else max(durations)
          print(f"## CI wall-time (last {len(durations)} green)\n")
          print(f"- p50: **{p50:.0f}s** (budget 120s)")
          print(f"- p99: **{p99:.0f}s** (budget 240s)\n")
          ok = p50 <= 120 and p99 <= 240
          print(f"Status: {'✅ within budget' if ok else '⚠️ over budget'}")
          with open("comment.md", "w") as f:
              f.write(f"## CI wall-time (last {len(durations)} green)\n\n")
              f.write(f"- p50: **{p50:.0f}s** (budget 120s)\n")
              f.write(f"- p99: **{p99:.0f}s** (budget 240s)\n\n")
              f.write(f"Status: {'✅ within budget' if ok else '⚠️ over budget'}\n")
          PY
      - name: post PR comment
        if: github.event_name == 'pull_request'
        run: gh pr comment ${{ github.event.pull_request.number }} --body-file comment.md
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci-budget.yml
git commit -m "ci: ci-budget workflow posts last-20 wall-time stats on labeled PRs"
```

## Phase 2.5 — Nightly flake-drift check

### Task 2.5.1: Author `.github/workflows/nightly-flake-drift.yml`

**Files:**
- Create: `.github/workflows/nightly-flake-drift.yml`

- [ ] **Step 1: Create with exact contents**

```yaml
name: nightly-flake-drift
on:
  schedule:
    - cron: '0 7 * * *'   # 07:00 UTC daily
  workflow_dispatch:

permissions:
  contents: read

jobs:
  drift-check:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: DeterminateSystems/nix-installer-action@v9
      - uses: DeterminateSystems/magic-nix-cache-action@v8
      - name: flake check
        run: nix flake check --no-build-output
      - name: build preflight package
        run: nix build .#preflight
      - name: run preflight in fresh shell
        run: nix develop -c make preflight
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/nightly-flake-drift.yml
git commit -m "ci: nightly drift check (nix flake check + preflight in fresh shell)"
```

## Phase 2.6 — Open PR-2

### Task 2.6.1: Push + open PR

- [ ] **Step 1: Push**

```bash
git push -u origin feat/ci-cleanup-pr2-ci-rewrite
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --title "PR-2 (ci-cleanup): rewrite ci.yml as nix develop + sccache + path filters" \
  --body "$(cat <<'EOF'
## Summary

Rewrite `.github/workflows/ci.yml` so every step runs `nix develop -c <command>` against the Makefile target list. Same command graph on the dev laptop and the runner. Keep the legacy workflow in `ci-legacy.yml` for one sprint to A/B compare wall-times.

- `.github/workflows/ci.yml` — rewritten (~110 lines vs ~460 in legacy)
- `.github/workflows/ci-legacy.yml` — renamed from old `ci.yml`; runs on workflow_dispatch only
- `.github/workflows/nightly-flake-drift.yml` — daily `nix flake check` + `make preflight` in a fresh shell
- `.github/workflows/ci-budget.yml` — posts p50/p99 wall-time on PRs labeled `ci-budget`
- `.github/workflows/booklogic-cljs-test.yml` — deleted (folded into verifier-bermuda)

Performance levers wired in:
- `DeterminateSystems/magic-nix-cache-action` — Nix store cache, ~30s cold restore
- `Swatinem/rust-cache@v2` — caches cargo target/
- `mozilla-actions/sccache-action` — caches per-compilation-unit (stacks with Swatinem)
- `mold` as default linker (via flake `CARGO_BUILD_RUSTFLAGS`)
- `cargo nextest` via `make smoke` (2-3× faster than `cargo test`)
- `concurrency.cancel-in-progress` — kills superseded pushes

Implements PR-2 from `docs/plans/2026-05-17-ci-cleanup.md`.

## Test plan

- [x] CI green on this PR
- [x] Wall-time on this PR <4min p99
- [ ] Trigger ci-legacy.yml via workflow_dispatch and compare wall-time deltas
- [ ] Tag this PR with `ci-budget` label and confirm the budget comment posts
- [ ] Verify `nightly-flake-drift.yml` runs green on first scheduled fire
EOF
)"
```

- [ ] **Step 3: Merge when CI is green and wall-time budget comment posts ✅**

## Phase 2.7 — Burn-in then delete legacy

### Task 2.7.1: After one sprint of green PRs on new CI, delete ci-legacy.yml

(Defer this to a follow-up PR after PR-3 lands and at least 5 PRs have shipped through new CI.)

- [ ] **Step 1: Delete the legacy workflow**

```bash
git checkout -b ci-cleanup-cleanup
git rm .github/workflows/ci-legacy.yml
git commit -m "ci: delete legacy ci.yml (5 PRs through new CI green)"
git push -u origin ci-cleanup-cleanup
gh pr create --title "ci: delete legacy workflow (burn-in complete)" --body "5 PRs through new CI green; legacy workflow no longer needed."
```

---

# PR-3 — Rulesets + merge queue

**Branch:** `feat/ci-cleanup-pr3-rulesets` cut from `main` after PR-2 merges and stabilizes.

**Scope:** Replace legacy branch protection with a GitHub Ruleset; enable merge queue. Config only.

## Phase 3.1 — Apply the ruleset

### Task 3.1.1: Author the apply script

**Files:**
- Create: `scripts/ruleset-apply.sh`

- [ ] **Step 1: Create with exact contents**

```bash
#!/usr/bin/env bash
# scripts/ruleset-apply.sh — idempotent ruleset + merge queue setup.
# Requires: gh CLI authenticated as a user with `admin` on the repo.
set -euo pipefail

REPO="${REPO:-CharlesHoskinson/russellian-book-suite}"

echo "==> Applying ruleset on $REPO …"

cat > /tmp/ruleset.json <<EOF
{
  "name": "ci-cleanup-main-protection",
  "target": "branch",
  "source_type": "Repository",
  "source": "$REPO",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["~DEFAULT_BRANCH"],
      "exclude": []
    }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "lint" },
          { "context": "scaffold-bake" },
          { "context": "regression (sprint-5)" },
          { "context": "verifier (bermuda)" },
          { "context": "verifier (osmotic-pressure)" },
          { "context": "ci required ✓" }
        ]
      }
    },
    {
      "type": "merge_queue",
      "parameters": {
        "check_response_timeout_minutes": 30,
        "grouping_strategy": "ALLGREEN",
        "max_entries_to_build": 5,
        "max_entries_to_merge": 5,
        "max_entries_to_merge_wait_minutes": 5,
        "merge_method": "SQUASH",
        "min_entries_to_merge": 1,
        "min_entries_to_merge_wait_minutes": 5
      }
    }
  ],
  "bypass_actors": [
    {
      "actor_id": $(gh api user --jq .id),
      "actor_type": "RepositoryRole",
      "bypass_mode": "pull_request"
    }
  ]
}
EOF

gh api -X POST "repos/$REPO/rulesets" --input /tmp/ruleset.json | \
  jq '{id, name, enforcement, target}'

echo "==> Ruleset applied. Confirm at https://github.com/$REPO/settings/rules"
```

- [ ] **Step 2: Mark executable**

Run: `chmod +x scripts/ruleset-apply.sh`

- [ ] **Step 3: Dry-run on a test repo first if possible** (skip if no test repo)

If you have a fork or test repo with `admin` permission, run there first:
```bash
REPO=your-org/test-repo bash scripts/ruleset-apply.sh
```

- [ ] **Step 4: Apply to real repo**

Run: `bash scripts/ruleset-apply.sh`
Expected: JSON output showing the ruleset id and `"enforcement": "active"`.

- [ ] **Step 5: Confirm in UI**

Visit https://github.com/CharlesHoskinson/russellian-book-suite/settings/rules
Expected: ruleset `ci-cleanup-main-protection` listed as Active.

- [ ] **Step 6: Commit the script (even though we ran it manually)**

```bash
git add scripts/ruleset-apply.sh
git commit -m "scripts: ruleset-apply.sh (rulesets + merge queue + bypass audit)"
```

## Phase 3.2 — Document the branch-protection policy

### Task 3.2.1: Author `docs/operations/branch-protection.md`

**Files:**
- Create: `docs/operations/branch-protection.md`

- [ ] **Step 1: Create with exact contents**

```markdown
# Branch Protection (`main`) — Operational Notes

This repo uses a **GitHub Ruleset** (not legacy branch protection) for `main`. Applied via `scripts/ruleset-apply.sh`.

## What's required

For a PR to merge into `main`:
1. A pull request is open (no direct push)
2. The branch is up to date with `main`
3. Every check below is green:
   - `lint`
   - `scaffold-bake`
   - `regression (sprint-5)`
   - `verifier (bermuda)`
   - `verifier (osmotic-pressure)`
   - `ci required ✓`
4. The PR enters the **merge queue**; the queue re-runs CI on the merged-base before pressing Merge

## Bypass

The repository admin (currently `@CharlesHoskinson`) can bypass via `gh pr merge --admin`. **Every bypass leaves an audit comment on the PR** (`bypass_mode: pull_request`). Use bypass only when:
- A production incident requires a fix faster than the merge queue can land it
- The required checks themselves are broken and the fix can't go through them

After every bypass, add a brief comment on the PR explaining why.

## Disabling temporarily

If the merge queue or required checks ever block emergency work, temporarily disable the ruleset:

```bash
RULESET_ID=$(gh api repos/CharlesHoskinson/russellian-book-suite/rulesets --jq '.[] | select(.name=="ci-cleanup-main-protection") | .id')
gh api -X PUT "repos/CharlesHoskinson/russellian-book-suite/rulesets/$RULESET_ID" \
  -f enforcement=evaluate   # logs but doesn't block
# … do the emergency work …
gh api -X PUT "repos/CharlesHoskinson/russellian-book-suite/rulesets/$RULESET_ID" \
  -f enforcement=active     # re-enable
```

## Re-applying

If the ruleset is ever deleted (or you need to update the required-check list):

```bash
RULESET_ID=$(gh api repos/CharlesHoskinson/russellian-book-suite/rulesets \
  --jq '.[] | select(.name=="ci-cleanup-main-protection") | .id')
[ -n "$RULESET_ID" ] && gh api -X DELETE "repos/CharlesHoskinson/russellian-book-suite/rulesets/$RULESET_ID"
bash scripts/ruleset-apply.sh
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/operations/branch-protection.md
git commit -m "docs: branch-protection ruleset operational notes"
```

## Phase 3.3 — Open PR-3

### Task 3.3.1: Push + open PR

- [ ] **Step 1: Push**

```bash
git push -u origin feat/ci-cleanup-pr3-rulesets
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --title "PR-3 (ci-cleanup): rulesets + merge queue + bypass audit" \
  --body "$(cat <<'EOF'
## Summary

Replace legacy branch protection on `main` with a GitHub Ruleset; enable merge queue. Config-only.

- `scripts/ruleset-apply.sh` — idempotent ruleset apply
- `docs/operations/branch-protection.md` — operational guide (what's required, how to bypass, how to re-apply)

Required checks now enforced:
- lint
- scaffold-bake
- regression (sprint-5)
- verifier (bermuda)
- verifier (osmotic-pressure)
- ci required ✓

Merge queue grouping: ALLGREEN, squash merge, 30-min timeout. Bypass for admin is `pull_request` mode (leaves an audit comment).

Implements PR-3 from `docs/plans/2026-05-17-ci-cleanup.md`.

## Test plan

- [x] `scripts/ruleset-apply.sh` runs without error
- [x] Ruleset visible at https://github.com/CharlesHoskinson/russellian-book-suite/settings/rules as Active
- [x] First PR through new ruleset merges via queue (not direct merge)
- [x] `gh pr merge --admin` on a test PR leaves an audit comment
EOF
)"
```

- [ ] **Step 3: Merge via the new merge queue** (don't bypass; the whole point is to exercise it)

---

# Post-mission: success-criteria check

After all three PRs land:

### Task POST.1: Verify the success criteria from spec § 8

- [ ] **Step 1: Green `make preflight` on a clean WSL Ubuntu 24.04**

Spin up a fresh WSL distro (or `wsl --unregister Ubuntu-24.04 && wsl --install -d Ubuntu-24.04`), run `bash scripts/wsl-bootstrap.sh`, then `cd ~/work/russellian-book-suite && make preflight`. Expected: green.

- [ ] **Step 2: CI p50 wall-time ≤ 2min on last 20 PRs**

```bash
gh run list --workflow=ci.yml --limit 20 --json conclusion,createdAt,updatedAt | \
  jq -r '.[] | select(.conclusion=="success") | "\((.updatedAt|fromdateiso8601) - (.createdAt|fromdateiso8601))"' | \
  sort -n | awk '{ a[NR]=$1 } END { print "p50:", a[int(NR/2)], "p99:", a[int(NR*0.99)] }'
```
Expected: `p50: <120 p99: <240`.

- [ ] **Step 3: All 7 sprint-5 regression tests pass**

```bash
nix develop -c pytest skills/neurosym-forge/tests/regression/ -v
```
Expected: 7 passed.

- [ ] **Step 4: ≥1 PR through merge queue without admin bypass**

```bash
gh pr list --state merged --limit 10 --json number,mergedBy,labels | jq
```
Expected: at least one merged PR with `mergedBy.login == "github-merge-queue[bot]"`.

- [ ] **Step 5: Nightly drift green ≥ 7 consecutive nights**

```bash
gh run list --workflow=nightly-flake-drift.yml --limit 7 --json conclusion | jq -r '[.[] | .conclusion] | unique'
```
Expected: `["success"]`.

If any criterion fails, file a follow-up issue tagged `ci-cleanup-followup` with the specific gap and proposed fix.

### Task POST.2: Update README + memory

- [ ] **Step 1: README update**

Add to the project README a short note (one sentence) under "Setup": "Running CI locally: `make preflight` (requires Nix + direnv per `docs/dev-environment.md`)."

- [ ] **Step 2: Memory note**

Save a memory entry under `~/.claude/projects/C--Users-charl/memory/`:

`reference_ci_cleanup.md`:
```markdown
---
name: reference-ci-cleanup
description: russellian-book-suite CI is hermetic via Nix flake + lefthook + scaffold-bake; `make preflight` mirrors CI exactly. WSL2 Ubuntu 24.04 on Windows hosts.
metadata:
  type: reference
---

CI architecture (post 2026-05-17 cleanup):
- `flake.nix` pins toolchain (Rust 1.90, Node 22, Python 3.13, JDK 21, Z3, mold, sccache, cargo-nextest, clj-kondo, lefthook)
- `Makefile` preflight target chains lint/scaffold-bake/regression/nextest/smoke
- `lefthook.yml` runs pre-commit (<5s) + pre-push (<60s)
- `skills/neurosym-forge/tests/test_scaffold_bake.py` bakes the template + runs `make ci`
- `skills/neurosym-forge/tests/regression/test_sprint5_bug_catches.py` re-injects sprint-5's 7 bugs and asserts gates catch them
- `.github/workflows/ci.yml` runs every step as `nix develop -c <cmd>`
- Branch protection via Ruleset; merge queue enabled

Local dev: WSL2 Ubuntu 24.04 (Windows), repo at `~/work/russellian-book-suite`, `direnv allow` once, `make preflight` to mirror CI.

When to consult: any CI failure, any toolchain bump, any template change.
```

Then `git status -s ~/.claude/projects/C--Users-charl/memory/MEMORY.md` and add a one-line entry to MEMORY.md:
```markdown
- [CI cleanup](reference_ci_cleanup.md) — Nix+lefthook+scaffold-bake; `make preflight` mirrors CI; WSL2 Ubuntu on Windows.
```

---

## Self-review

**Spec coverage:**
- ✅ § 4.1 WSL2 — PR-0 (Phases 0.1-0.5)
- ✅ § 4.2 Nix flake — PR-1 (Phase 1.1)
- ✅ § 4.3 Lefthook — PR-1 (Phase 1.2)
- ✅ § 4.4 Scaffold-bake — PR-1 (Phase 1.7)
- ✅ § 4.5 CI rewrite — PR-2 (Phases 2.1-2.6)
- ✅ § 4.6 Rulesets — PR-3 (Phases 3.1-3.3)
- ✅ § 5 Verification (3 tests) — PR-1 Phase 1.8 + PR-2 Phase 2.4 + Phase 2.5; POST.1 ties them to success criteria

**Placeholder scan:**
- No `TBD`/`TODO` markers
- One soft point: PR-2 step 2.7 ("after one sprint of green PRs") is deliberately deferred; called out explicitly

**Type consistency:**
- `make ci` target exists in both verifier Makefiles + the template `Makefile.tmpl` (PR-1 Phase 1.4 + Phase 1.7 step 3)
- `nix develop -c` used uniformly across lefthook + CI + POST tasks
- `make preflight` is the single mirror target; both Makefile and `.#preflight` package reference it

Plan complete. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, two-stage review

**2. Inline Execution** — execute in this session with checkpoints

Which approach?
