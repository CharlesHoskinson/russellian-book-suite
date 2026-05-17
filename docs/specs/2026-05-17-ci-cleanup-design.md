# CI Pipeline Cleanup Design — Post Sprint-5 Thrash

**Date:** 2026-05-17
**Status:** Draft (brainstorming output, pending user review)
**Author:** russellian-book-suite maintainers
**Supersedes:** ad-hoc CI evolution since v0.3
**Successor plan:** `docs/plans/2026-05-17-ci-cleanup.md` (to be written by writing-plans skill)

## 1. Goal

Make the russellian-book-suite CI pipeline:

- **Fast** — common-path PRs land in under 2 minutes p50, 4 minutes p99.
- **Reliable** — the same six classes of bug that thrashed sprint 5 are caught locally (before push) or fail the *first* CI run with a clear signal.
- **Hard to regress** — every cleanup carries a regression test that fails if the gate is removed.

Out of scope: shipping new product features; rewriting bermuda or osmotic-pressure verifier logic.

## 2. Sprint-5 thrash post-mortem

PR #59 (osmotic-pressure verifier) required six push-fix-push cycles spanning ~60 minutes of wall time before merge. Failure timeline:

| # | Failure | Root cause | Sprint-time class |
|---|---|---|---|
| 1 | `napi build --platform` exits non-zero | Stale `package.json` template; sprint 4 already moved bermuda to cargo+cp but didn't update the neurosym-forge template | **Template drift** |
| 2 | shadow-cljs: `Resource does not have expected namespace osmotic-pressure.core` | CLJS `(ns foo_bar)` convention requires dashed namespace for underscore filenames; template hardcoded `{{ project_slug }}` (underscore) in `ns` declarations | **Template drift** |
| 3 | `nbb -m osmotic_pressure.booklogic` exits non-zero | CI workflow step hardcoded the underscore module name after the dash rename | **Workflow drift** |
| 4 | `test_slug_substitution` AssertionError | Test asserted the old underscore namespace after the rename | **Test drift** |
| 5 | shadow-cljs: `The required JS dependency "../native/X.node" is not available` | `["../X.node" :as native]` resolves relative to source file at compile time, not to dist/ at runtime — bermuda's `:test` build never exercised this code path | **Template drift (uncovered by first end-to-end exerciser)** |
| 6 | CLJS compile: `Use of undeclared Var phases/slurp` | `slurp` is Clojure-only, not in cljs.core; template's `phases.cljs.tmpl` had been wrong since v0.3 | **Template drift** |
| 7 | Python `re.PatternError: unknown extension ?<v` | `lifts.edn` uses JS-style `(?<name>)` named groups; Python `re` needs `(?P<name>)` — no compat layer between the two boundaries | **Cross-language regex impedance** |

### Common thread

Four of seven failures are *template drift*: the neurosym-forge scaffolded project template had latent bugs in `package.json.tmpl`, the `.cljs.tmpl` namespace declarations, `bridge.cljs.tmpl`, and `phases.cljs.tmpl` that no test ever exercised. Bermuda's CI only ran `shadow-cljs compile test` (the `:test` build) — which sidesteps `bridge.cljs`, `phases.cljs`, the `.node` require, and the full lift chain. Sprint 5 was the **first time** the template was end-to-end tested. Every latent bug surfaced at once, on the canonical Linux gate, in 5-minute increments.

The other three failures are *parity gaps* — Windows local dev can't build a `.so`, can't run the Linux `.node` linker, and didn't catch the JS↔Python regex mismatch because no test compiles a synthesized regex through the Python ingester.

### Cost analysis

- 6 cycles × ~5 minutes per CI smoke = 30 minutes pure CI wait
- 6 fix-investigate cycles × ~5 minutes per = 30 minutes maintainer time
- 1 admin-merge to escape the cycle, leaving the last smoke unverified
- ~60 minutes total wall time on a sprint that should have been a 10-minute formality

## 3. Architecture

Six stacked layers, each with one job. Same command graph executes in two places (dev laptop + GitHub runner).

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 6 — Branch protection (GitHub Rulesets + merge queue)     │
│   Required: lint, scaffold-bake, verifier-{bermuda,osmotic},    │
│             neurosym-forge-offline. Auditable bypass via PR     │
│             label. No more silent --admin merges.               │
├─────────────────────────────────────────────────────────────────┤
│ Layer 5 — GitHub Actions CI (ci.yml, one workflow)              │
│   runs-on: ubuntu-24.04 (+ arm64 where toolchain supports it)   │
│   concurrency: cancel-in-progress                               │
│   every step: nix develop -c <command>                          │
│   sccache + Swatinem/rust-cache + setup-mold + cargo-nextest    │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4 — Scaffold bake-and-test                                │
│   pytest test_scaffold_bake.py: instantiate template,           │
│   run generated project's full `make ci` end-to-end             │
│   Runs in CI on template-touching PRs; also in pre-push         │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3 — Local pre-flight gates (lefthook)                     │
│   pre-commit (<5s): clj-kondo, ruff, cargo fmt, regex-compile   │
│   pre-push (<60s): scaffold-bake, nextest changed, smoke chg    │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2 — Hermetic toolchain (flake.nix devShell)               │
│   Pinned: Rust 1.90, Node 22, Python 3.13, OpenJDK 21, Z3,      │
│           nbb, shadow-cljs deps, mold, sccache, clj-kondo,      │
│           lefthook, cargo-nextest, ruff                         │
│   Cachix substituter for cold-start <30s in CI                  │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1 — WSL2 Ubuntu 24.04 (Windows dev host only)             │
│   ext4 repo at ~/work/russellian-book-suite (not /mnt/c)        │
│   .wslconfig: mirrored networking, sparseVhd, autoMemoryReclaim │
│   VS Code Remote-WSL for editing                                │
│   .gitattributes enforces LF eol                                │
└─────────────────────────────────────────────────────────────────┘
```

**Same command graph, two sites:** `make preflight` on the laptop and the CI workflow both execute `nix develop -c <step>` with byte-identical step lists. Green-on-laptop ⇒ green-in-CI is the contract.

## 4. Components

### 4.1 Layer 1 — WSL2 Ubuntu 24.04 (Windows dev only)

**Decisions:**

- **Distro:** Ubuntu 24.04 LTS — byte-matches `runs-on: ubuntu-24.04` GH runner, preserves `apt install` escape hatch for ad-hoc tools (`perf`, `valgrind`, `gh`, `htop`). Rejected NixOS-WSL because eliminating `apt` is too restrictive for a polyglot research repo.
- **Repo location:** `~/work/russellian-book-suite` on ext4. Cross-OS DrvFs (`/mnt/c/...`) is ~6% of native throughput; cargo+node_modules go from 4min → 15s incremental.
- **VS Code Remote-WSL** for editing — Unix socket, native fs watches, zero workflow regression vs. current Windows-side editing.
- **`.wslconfig`** at `%USERPROFILE%\.wslconfig`:
  ```ini
  [wsl2]
  memory=24GB
  processors=12
  swap=8GB
  networkingMode=mirrored
  dnsTunneling=true
  autoProxy=true
  sparseVhd=true
  [experimental]
  autoMemoryReclaim=gradual
  ```
- **Git credentials** via Windows GCM bridged into WSL:
  ```ini
  [credential]
      helper = /mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager.exe
  [core]
      autocrlf = false
      eol = lf
  ```
- **`.gitattributes`** at repo root: `* text=auto eol=lf` plus explicit `*.png binary`, `*.node binary`, `*.jar binary`, `*.so binary`. One-time `git add --renormalize .` after.
- **Backup:** `wsl --export Ubuntu-24.04 D:\backups\ubuntu-YYYY-MM-DD.tar` weekly. Tested-restore quarterly.

**Ships in PR-0** (WSL bootstrap — docs + scripts only, zero code changes).

### 4.2 Layer 2 — Hermetic toolchain (Nix flake)

Single `flake.nix` at repo root. One `devShell` aggregates everything CI needs:

```nix
{
  description = "russellian-book-suite hermetic dev environment";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
    rust-overlay.url = "github:oxalica/rust-overlay";
  };
  outputs = { self, nixpkgs, flake-utils, rust-overlay }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; overlays = [ rust-overlay.overlays.default ]; };
        rust = pkgs.rust-bin.stable."1.90.0".default.override {
          extensions = [ "rust-src" "clippy" "rustfmt" ];
        };
      in {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            rust mold sccache cargo-nextest
            nodejs_22 nodePackages.pnpm
            python313 python313Packages.pip ruff
            jdk21 clj-kondo babashka
            z3 cmake gnumake
            lefthook git gh
          ];
          shellHook = ''
            export RUSTC_WRAPPER=sccache
            export CARGO_BUILD_RUSTFLAGS="-C link-arg=-fuse-ld=mold"
            export PATH="$HOME/.cargo/bin:$PATH"
            export NBB_PATH="$PWD/.nbb"
          '';
        };
        packages.preflight = pkgs.writeShellApplication {
          name = "preflight";
          text = "make -C $PWD preflight";
        };
        checks.flake-drift = pkgs.runCommand "flake-drift-check" {} ''
          # asserts ci.yml step list == makefile preflight target steps
          diff ${./scripts/ci-steps.txt} ${./Makefile-preflight-steps.txt}
          touch $out
        '';
      });
}
```

- **Pin policy:** all toolchains pinned by version + nixpkgs revision. `flake.lock` committed.
- **Cachix:** `russellian-book-suite.cachix.org` public substituter. CI populates it; cold-start in fresh runner drops from 8min toolchain install to ~30s download.
- **Direnv:** `.envrc` with `use flake` — `cd` into repo auto-loads shell on laptop.

**Ships in PR-1.**

### 4.3 Layer 3 — Local pre-flight (lefthook)

Single `lefthook.yml`, two stages:

```yaml
pre-commit:
  parallel: true
  commands:
    clj-kondo:
      glob: "*.{clj,cljs,cljc,edn}"
      run: clj-kondo --lint {staged_files}
    ruff:
      glob: "*.py"
      run: ruff check {staged_files}
    cargo-fmt:
      glob: "*.rs"
      run: cargo fmt --check -- {staged_files}
    regex-compile:
      glob: "verifiers/*/rules/booklogic/lifts.edn"
      run: nix develop -c python scripts/regex-compile-check.py {staged_files}

pre-push:
  commands:
    scaffold-bake:
      run: nix develop -c pytest skills/neurosym-forge/tests/test_scaffold_bake.py
    nextest-changed:
      run: nix develop -c cargo nextest run --workspace --no-fail-fast
    smoke-changed:
      glob: "verifiers/**"
      run: nix develop -c make smoke-changed
```

Rationale per gate:

| Gate | Sprint-5 bug it catches | Cost |
|---|---|---|
| `clj-kondo` | #2 (CLJS namespace), #6 (`slurp` undeclared) | <2s |
| `ruff` | future Python lints | <1s |
| `cargo fmt` | format drift | <1s |
| `regex-compile` | #7 (JS vs Python regex) | <1s |
| `scaffold-bake` | #1, #2, #3, #5 (template drift) | ~30s |
| `nextest-changed` | logic regressions | varies |
| `smoke-changed` | end-to-end .node + cljs bundle | ~60s |

**Why lefthook over pre-commit/husky:** Go binary, parallel by default, polyglot-aware, single YAML. Research benchmarks show 2.7× faster than Husky on polyglot monorepos. No `npm install` bootstrap requirement (Husky needs Node; pre-commit needs Python venv per hook).

**Ships in PR-1** alongside the flake.

### 4.4 Layer 4 — Scaffold bake-and-test

Single test that instantiates the neurosym-forge template into a tmpdir and runs the generated project's full `make ci`:

```python
# skills/neurosym-forge/tests/test_scaffold_bake.py
def test_baked_scaffold_passes_full_ci(tmp_path):
    """REQ-SCAFFOLD-BAKE-001: A freshly scaffolded project passes
    `make ci` end-to-end (booklogic-compile + codegen + cargo build
    + shadow-cljs release main + pytest smoke).
    """
    scaffold_project(
        project_name="Bake Test",
        project_slug="bake_test",
        out_dir=tmp_path / "bake_test",
        skill_root=SKILL_ROOT,
    )
    # Copy a known-good rules tree + fixtures into the bake (we keep a
    # minimal smoke ruleset alongside the template for this purpose).
    copy_smoke_rules(tmp_path / "bake_test")
    result = subprocess.run(
        ["make", "ci"], cwd=tmp_path / "bake_test",
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"baked scaffold failed `make ci`:\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
```

CI runs this on every PR that touches `skills/neurosym-forge/assets/project-template/**` (path-filtered). Locally it runs in `pre-push`. Sprint 5 bugs #1, #2, #3, #5 are all caught by this single test.

**Bonus:** bermuda CI also adds `npm run build` (full `:main` shadow-cljs bundle) so the `.node`-chain + `slurp` class of bug surfaces in bermuda CI long before the next osmotic-style sprint.

**Ships in PR-1.**

### 4.5 Layer 5 — CI workflow rewrite

Single `.github/workflows/ci.yml`. Every job:

```yaml
runs-on: ubuntu-24.04   # ubuntu-24.04-arm where the toolchain supports it
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
steps:
  - uses: actions/checkout@v4
  - uses: DeterminateSystems/nix-installer-action@v9
  - uses: DeterminateSystems/magic-nix-cache-action@v8
  - uses: cachix/cachix-action@v15
    with: { name: russellian-book-suite, signingKey: '${{ secrets.CACHIX_SIGNING_KEY }}' }
  - uses: Swatinem/rust-cache@v2
  - uses: mozilla-actions/sccache-action@v0.0.7
  - run: nix develop -c <step-from-makefile>
```

Job matrix:

| Job | Triggers | Wall-time target |
|---|---|---|
| `lint` | every PR | <30s |
| `scaffold-bake` | PRs touching `skills/neurosym-forge/assets/project-template/**` or `flake.nix` | <2min |
| `verifier-bermuda` | PRs touching `verifiers/bermuda/**` | <2min warm / <5min cold |
| `verifier-osmotic` | PRs touching `verifiers/osmotic_pressure/**` | <2min warm / <5min cold |
| `python-skill-matrix` | PRs touching `skills/{book-*,russellian-style,review-conductor,neurosym-forge}/**` | <3min |
| `cljs-integration` | PRs touching `**/*.cljs` or `**/shadow-cljs.edn` | <3min |

Drop:
- `bermuda informational lints` (collapsed into `verifier-bermuda`)
- Triplicate Python version matrix on every skill (run 3.13 only on PRs; 3.11+3.12 on `main` push)

**Performance levers from research:**

- **`mozilla-actions/sccache-action` + `Swatinem/rust-cache`** stack — Swatinem caches `target/`, sccache caches per-CU. 50-60% warm-cache hit rate cuts builds in half.
- **`setup-mold@v1`** on biggest link steps (Rust 1.90 default `rust-lld` covers smaller ones for free).
- **`cargo-nextest`** instead of `cargo test` — 2-3× faster, structured output, partition sharding.
- **`runs-on: ubuntu-24.04-arm`** where supported — 20-40% faster wall-clock for Rust, GA Aug 2025.
- **`concurrency: cancel-in-progress`** — kills superseded pushes; would have saved ~25min on sprint 5.

**Ships in PR-2.**

### 4.6 Layer 6 — Branch protection (Rulesets + merge queue)

Replace legacy branch protection on `main` with a Ruleset:

```yaml
target: main
enforcement: active
rules:
  pull_request:
    required_approving_review_count: 0  # solo maintainer
  required_status_checks:
    strict_required_status_checks_policy: true  # require up-to-date branches
    required_status_checks:
      - lint
      - scaffold-bake
      - verifier-bermuda
      - verifier-osmotic
      - python-skill-matrix
      - cljs-integration
  required_linear_history: false
  required_signatures: false
  merge_queue:
    check_response_timeout_minutes: 30
    grouping_strategy: ALLGREEN
    max_entries_to_build: 5
    merge_method: SQUASH
bypass_actors:
  - actor_id: <admin-team-id>
    actor_type: Team
    bypass_mode: pull_request   # logged as PR review comment
```

**Effect:** the maintainer can still `--admin` merge in true emergencies, but every bypass leaves an audit comment on the PR. The merge queue removes the temptation by guaranteeing PRs aren't blocked by stale-base CI failures.

**Ships in PR-3.**

## 5. Verification — how we know it works

Three concrete tests for the cleanup itself:

1. **Synthetic-bug regression suite** (`tests/regression/test_sprint5_bug_catches.py`):
   Re-inject each of the 7 sprint-5 bugs in a throwaway branch and assert the correct gate (pre-commit / pre-push / CI / scaffold-bake) fails. Lives in `skills/neurosym-forge/tests/regression/`. Runs in CI nightly.

2. **Wall-time budget assertion** (`.github/workflows/ci-budget.yml`):
   A tiny workflow that runs `gh run list --workflow=ci.yml --limit=20 --json conclusion,createdAt,updatedAt` and posts a PR comment if p50 wall-time for the last 20 runs exceeded budget (2min p50 / 4min p99). Non-blocking; visibility only.

3. **Hermetic-build proof** (`.github/workflows/nightly-flake-drift.yml`):
   Nightly job runs `nix flake check --no-build-output` + `nix build .#preflight` in a fresh container. Fails if `flake.lock` has drifted from any CI command, or if `ci.yml` references a tool not in the flake. This is the gate that prevents Layer-5 drift from Layer-2.

## 6. Migration plan (four PRs, each independently mergeable)

| PR | Title | Scope | Risk | Rollback |
|---|---|---|---|---|
| PR-0 | docs+scripts: WSL bootstrap | `docs/dev-environment.md`, `scripts/wsl-bootstrap.sh`, `.gitattributes`, `.wslconfig.example` | None — pure docs | Revert PR-0 |
| PR-1 | nix+lefthook+scaffold-bake | `flake.nix`, `flake.lock`, `lefthook.yml`, `.envrc`, `skills/neurosym-forge/tests/test_scaffold_bake.py`, regression suite | Low — existing CI keeps working; devs get fast local gates as opt-in (`lefthook install`) | Revert PR-1 |
| PR-2 | CI rewrite to nix develop | `.github/workflows/ci.yml`, `.github/workflows/nightly-flake-drift.yml`, `Makefile` (preflight target) | Medium — keep old `ci-legacy.yml` in parallel for one sprint (A/B compare wall-time + green-rate) | Revert PR-2; legacy workflow continues |
| PR-3 | Rulesets + merge queue | Repo-level GitHub config via `gh ruleset` + UI for merge queue toggle | Low — config only | Restore legacy branch protection via `gh ruleset` |

After PR-2 stabilizes (one sprint of green runs), delete `ci-legacy.yml`.

## 7. Risks + open questions

| Risk | Mitigation |
|---|---|
| Nix flake adoption tax — maintainer unfamiliar with Nix syntax | PR-1 ships with a `docs/nix-cheatsheet.md` covering the 10 commands needed for daily work. No new contributors are forced to learn Nix beyond `direnv allow` and `nix develop`. |
| `sccache` + Cachix secrets require GitHub repo secrets configuration | One-time setup in PR-2; documented in `docs/dev-environment.md`. Falls back to no-cache if secrets absent (warmer-than-cold still beats current). |
| WSL2 migration risks losing local-only state | `wsl --export` weekly + `wsl --import` rehearsal documented. Repo work-in-progress pushed to personal fork branches so worst case is unpushed commits. |
| Merge queue may delay urgent fixes | Bypass via `--admin` remains; audited via Ruleset bypass comment. |
| `arm64` runners may lack action support | Per-job decision; jobs that fail on arm64 fall back to `ubuntu-24.04`. Documented in workflow comments. |

## 8. Success criteria

The cleanup is done when:

- ✅ `make preflight` runs to green on a clean WSL Ubuntu 24.04 with only `flake.nix` + `direnv` + `lefthook` installed
- ✅ CI p50 wall-time on the last 20 PRs is ≤ 2 min (was ~8 min on sprint 5)
- ✅ Every one of the 7 sprint-5 bugs is caught by the regression suite at its expected gate
- ✅ At least one PR ships through the merge queue without `--admin` bypass
- ✅ `nightly-flake-drift` has run green for 7 consecutive nights

## 9. Non-goals (explicit)

This cleanup will not:

- Rewrite any verifier (bermuda, osmotic-pressure) logic
- Migrate any skill from pytest to nextest or vice versa
- Change the published artifact format or release process
- Switch from Cachix to self-hosted Nix binary cache
- Add new product features
- Migrate from GitHub Actions to a different CI provider

---

**End of design.** Successor plan to be authored by writing-plans skill: `docs/plans/2026-05-17-ci-cleanup.md`.
