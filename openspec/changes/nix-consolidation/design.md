# Design: nix-consolidation

## 0. Current state

Nix's role today: toolchain provisioner. `flake.nix` (flake-utils,
nixpkgs 25.05, rust-overlay) exposes one monolithic devShell, a
`packages.preflight` wrapper, and a single check (`flake-drift`) that
diffs `scripts/ci-steps.txt` against `make -n preflight`. CI jobs `lint`
and `preflight` run `nix develop -c make ...`; `cargo-test` and the
python-skill matrix bypass Nix entirely. lefthook spawns a fresh
`nix develop` per hook command. magic-nix-cache backs all Nix jobs.

## 1. Decisions

**D1 — Deepen the hybrid.** Nix provisions toolchains; language-native
tools (pip, cargo, npm) manage packages and builds. Rejected: full-Nix
builds (uv2nix/crane) — large migration, Windows still needs a parallel
path, no current pain justifies it. Rejected: minimal touch — the
dual-source-of-truth and monolith costs are real maintenance drag.

**D2 — cache-nix-action replaces magic-nix-cache.** GHA-native
(`nix-community/cache-nix-action`): caches `/nix/store` via actions/cache
with GC-before-save, no external accounts, fastest of the three options
in published benchmarks. Requires Nix ≥ 2.24 (satisfied). Rejected:
Cachix free OSS tier (external account + signing key for marginal gain at
this scale); FlakeHub Cache (deeper Determinate lock-in, support-email
enrollment); staying on magic-nix-cache (deprecated, reverse-engineered
API).

**D3 — Flake checks are the canonical step list.** Every pure gate is a
`checks.*` derivation; `nix flake check` is the single lint entry point
locally and in CI. treefmt-nix and lefthook.nix each emit both the tool
config and a check from one definition, so hook/CI/formatter drift is
structurally impossible. `scripts/ci-steps.txt` and `checks.flake-drift`
are deleted. Rejected: Make stays canonical (keeps the shim and the
tension permanently); om ci (third-party orchestrator dependency for
capabilities `nix flake check` already covers at this scale).

**D4 — flake-parts layout.** Root `flake.nix` is thin; concerns live in
`nix/*.nix` modules. treefmt-nix and the hook integration ship as
flake-parts modules, so wiring is free. flake-utils is dropped
(`perSystem` replaces `eachSystem`; dead `forAllSystems` goes with it).
Rejected: plain hand-rolled `genAttrs` (Determinate school — hand-wires
what the modules give for free); single growing file (unclear boundaries
at the size this design implies).

**D5 — Stay on DeterminateSystems/nix-installer-action.** SHA-pinned as
today. It now installs Determinate Nix (upstream option ended January
2026); that is what CI has effectively run since the cutover, and
cache-nix-action's Nix ≥ 2.24 floor is met. Rejected:
cachix/install-nix-action (upstream purity is not worth the churn while
the Determinate distribution stays compatible).

**Sandbox rule (escape hatch for D3).** Pure → `checks.*`. Impure
(network, cargo builds, `npm ci`, writes outside the build dir) → Makefile
verb run via `nix develop -c`. If a check candidate proves sandbox-unsafe
during implementation, it falls back to the Makefile — never to a third
place.

## 2. Target flake architecture

```
flake.nix                 inputs + mkFlake { systems; imports = [ ./nix/... ]; }
nix/
├── toolchains.nix        rust   = rust-bin 1.90 + mold + sccache + cargo-nextest
│                                  + z3 + cmake + pkg-config
│                         python = python313.withPackages
│                                  (pytest, pytest-xdist, ruff, pyyaml, jinja2, psutil)
│                         cljs   = nodejs_22 + pnpm + babashka + jdk21 + clj-kondo
│                         core   = git + gh + jq + yq + curl + gnumake + lefthook
├── shells.nix            devShells.rust / .python / .cljs (toolchain + core)
│                         devShells.default = mkShell { inputsFrom = [ rust python cljs ]; }
│                         shellHook: only the cargo/mold exports kept from today
├── treefmt.nix           programs: nixpkgs-fmt, rustfmt, ruff-check (points at ruff.toml)
│                         → formatter.* (nix fmt) + checks.formatting
├── hooks.nix             lefthook.nix config: clj-kondo, treefmt-on-staged,
│                         regex-compile, readme-lint → generated hook config + checks.hooks
│                         (readme-lint is hook-only: it runs from tools/readme-lint/.venv,
│                         which is sandbox-unsafe — sandbox rule applies)
├── checks.nix            checks.clj-kondo        (whole tree, --fail-level error)
│                         checks.invariant-lint   (lint_no_direct_http +
│                                                  check_windows_canary + pytest ci/)
│                         checks.neurosym-drift   (test_support_matrix +
│                                                  test_induction_grammar_drift)
│                         checks.required-name    (scripts/check-required-name.sh)
└── preflight.nix         packages.preflight (nightly builds it; wraps the slim preflight)
```

Formatting churn is zero by construction: `ruff-check` only (no
ruff-format), `nixpkgs-fmt` kept (no nixfmt-rfc-style switch in this arc).

## 3. CI deltas

| Job | Today | After |
|---|---|---|
| lint | `nix develop -c make lint` + 3 ad-hoc invariant steps + required-name script | installer → cache-nix-action → `nix flake check -L` |
| preflight | `nix develop -c make preflight` (re-runs lint inside) | same command; preflight target is suites only — the lint double-run disappears |
| cargo-test (4 legs) | apt/brew z3 retry loops + dtolnay/rust-toolchain + Swatinem | installer → cache-nix-action → Swatinem → `nix develop .#rust -c cargo test --features smt ...` |
| python-skill-matrix | setup-python + pip venvs | unchanged (Windows forbids Nix; hybrid is deliberate) |
| actionlint / changes / compute-matrix / divergence / required | — | unchanged |

**Cache strategy.** cache-nix-action shares the 10 GB repo quota with
Swatinem, HF, spaCy, and npm caches. Controls: per-job
`gc-max-store-size` (lint/preflight cache the default-shell closure;
cargo-test only the rust shell — per-language shells also shrink cache
entries); primary key per OS/job-class from a hash of `flake.lock` +
`nix/`; `restore-prefixes-first-match` for partial hits. First lever
under quota pressure: dedupe the rust-shell entry across the four cargo
legs. Fallback: drop store caching on cargo legs — z3 substitutes from
cache.nixos.org.

## 4. Make, lefthook, nightly

**Makefile.** `preflight: scaffold-bake regression smoke-bermuda
smoke-osmotic`. New alias `lint: nix flake check`. `install-hooks`
becomes an alias for entering the devShell (hook install moves to
shellHook). The ci-steps.txt alignment header goes away.

**lefthook.** `lefthook.yml` deleted as a source file; generated from
`nix/hooks.nix`. Hook commands reference store paths directly (no
`nix develop` spawn per command). `.envrc` gains `watch_file nix/*.nix`
so nix-direnv keeps the evaluated shell cached. Known gotchas handled in
the module: `TERM=dumb` for git-invoked hooks, `LEFTHOOK_BIN` wrapper so
generated hooks resolve the pinned binary.

**nightly.** `drift-check` keeps its three steps (`nix flake check`,
`nix build .#preflight`, run preflight) — flake check now covers the
whole gate surface instead of one diff. Workflow renamed `nightly`
(PR 3). New leg `flake-check-arm` on `ubuntu-24.04-arm` (free for public
repos) runs `nix flake check`, making the declared `aarch64-linux`
support real. Nightly-only; PR latency untouched.

**New workflow (PR 1).** `flake-maintenance.yml`: weekly
update-flake-lock PR + flake-checker advisory.

## 5. PR staging

- **PR 1 — forced fixes.** Cache swap at all three sites; prune
  `forAllSystems`; add flake-maintenance; record D5. No step list moves —
  green by construction. Records wall-time and cache-hit baselines.
- **PR 2 — restructure.** flake-parts layout, treefmt-nix, checks
  migration, lint job → `nix flake check -L`, Makefile slims. The drift
  shim is deleted in the same commit that points the lint job at flake
  check — no window where neither mechanism guards.
- **PR 3 — hooks and edges.** lefthook.nix, cargo-test nix-ification,
  nightly rename + ARM leg, `.envrc` and runbook updates
  (docs/operations/ci-platforms.md).

Each PR is independently green and independently revertable.

## 6. Verification

**Gate-replay on every moved gate** (ruff, clj-kondo, three formatters,
both invariant linters, required-name, hooks): introduce a deliberate
violation on a scratch commit, confirm the new check goes red, revert.
Green alone proves nothing about a gate that silently stopped running
(the PR-122 lesson).

**Equivalence checks.** treefmt's ruff invocation diffed against
`ruff check .` on the full tree before PR 2 merges. The mapping
old-step → new-check is tabulated in PR 2's description; every row needs
a demonstrated red.

**Timing.** lint / preflight / cargo-test wall times and cache-hit rates
recorded per PR against the PR 1 baseline. macOS cargo legs trade brew z3
(~1 min, flaky) for nix install + store restore; if the trade is net
negative, revert path keeps brew on macOS only.

**Local.** `nix flake check` on WSL2 from an ext4 clone (`~/...`, never
`/mnt/c` — 9P overhead is an order of magnitude and would poison timing
sense). Nightly dispatched after each merge.

## 6b. As-built deviations (recorded post-merge)

- Hooks are generated by a self-contained `pkgs.formats.yaml` module
  (nix/hooks.nix) instead of the lefthook.nix input; hook names derive from
  the config attrset and shells.nix installs store-pinned hook scripts via
  `git rev-parse --git-path hooks` (worktree-safe), with a sweep for stale
  lefthook-era scripts.
- cargo-test's Swatinem step carries `cmd-format: "nix develop .#rust -c
  {0}"` — rust-cache probes `rustc -vV` on PATH and hard-fails without
  rustup; the format string routes the probe through the flake shell.
- The rust shell exports `LD_LIBRARY_PATH` for z3's lib output on Linux
  (rustc records no RPATH for pkg-config -L dirs); darwin resolves via
  absolute install_names.
- mold, its linker flag, and the export above are linux-gated (hotfix
  #217): mold is marked broken on darwin in nixpkgs 25.05.
- GC budgets set from measured closures: rust shell 4.0 GiB → 6G;
  default shell 5.1 GiB → 8G (the spec'd 5G was below the closure).
- The treefmt check self-names `checks.treefmt` (not `checks.formatting`);
  rustfmt runs with edition 2024; pre-commit rustfmt covers staged files
  only (whole-tree coverage stays in CI via the check).
- The pre-push `nextest-changed` hook was dropped at close-out: no
  top-level cargo workspace exists, so the inherited command errored on
  every push.

## 7. Risks

| Risk | Mitigation / fallback |
|---|---|
| 10 GB cache quota contention | §3 controls; fallback drops store caching on cargo legs |
| "Pure" check proves sandbox-unsafe | Sandbox rule: falls back to Makefile verb, design unchanged |
| lefthook.nix is a small-community dep | Thin YAML generator; fallback commits the generated lefthook.yml and reverts to hand-maintenance, or git-hooks.nix |
| macOS cargo legs gain nix-install cost | Measured in PR 3; revert path keeps brew on macOS only |
| treefmt ruff divergence | Equivalence diff before merge (§6) |
| Determinate Nix diverges from upstream | Low; D5 recorded, cachix/install-nix-action remains the documented exit |
