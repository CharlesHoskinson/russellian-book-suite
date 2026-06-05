# Proposal: nix-consolidation

## Why

Three pressures on the Nix layer, one forced and two structural:

1. **Forced.** All three Nix-using CI jobs (lint, preflight, nightly
   drift-check) depend on `magic-nix-cache-action`. Its free tier ended
   February 2025; the current version runs against a reverse-engineered,
   undocumented GitHub cache API that Determinate explicitly warns can
   break at any time. The cache layer must be replaced before it breaks,
   not after.
2. **Dual source of truth.** The CI step list lives in the Makefile and is
   mirrored into `scripts/ci-steps.txt`, policed by the `flake-drift`
   check. This detects divergence instead of making it impossible. The
   2025/26 consensus stack (treefmt-nix, lefthook.nix) derives hooks, CI
   checks, and formatter config from one Nix definition, so the shim and
   its check can be deleted rather than maintained.
3. **Monolith costs.** One devShell carries every toolchain (rust + JDK +
   node + python); a Python-skill contributor pays the full closure.
   `cargo-test` reinstalls z3 via apt/brew with hand-rolled retry loops
   while flake.nix already ships z3. `forAllSystems` is dead code;
   `aarch64-linux` is declared supported but nothing ever builds it.

## What

- **Cache (PR 1):** replace magic-nix-cache with
  `nix-community/cache-nix-action` at all three sites. Add a weekly
  `flake-maintenance` workflow (update-flake-lock + flake-checker) so the
  nixpkgs pin stops rotting silently. Prune `forAllSystems`.
- **Restructure (PR 2):** flake-parts layout under `nix/` (toolchains,
  shells, treefmt, hooks, checks, preflight). Everything in `make lint`
  plus the ad-hoc invariant-linter steps becomes a `checks.*` derivation;
  the lint job becomes `nix flake check -L`. Delete `scripts/ci-steps.txt`
  and `checks.flake-drift` in the same commit. Per-language devShells
  (`rust`, `python`, `cljs`) composed into `default`.
- **Hooks and edges (PR 3):** lefthook config generated from Nix
  (lefthook.nix), hooks reference store paths instead of spawning
  `nix develop` per command. `cargo-test` takes z3 and the rust toolchain
  from the flake (apt/brew/rustup deleted). Nightly gains a free
  `ubuntu-24.04-arm` flake-check leg, making the `aarch64-linux` claim
  real. Nightly renamed `nightly`.

The python-skill matrix stays Nix-free (Windows leg forbids Nix; the
hybrid is deliberate). Scaffold-bake, regression, and verifier smokes stay
Makefile verbs run via `nix develop -c` (sandbox-unsafe: cargo builds,
`npm ci`).

## Verification

Gate-replay on every moved gate: introduce a deliberate violation,
confirm the new check goes red, revert. Full matrix runs on each PR
(shared paths touched). Nightly dispatched after each merge. Wall-time
and cache-hit baselines recorded in PR 1, compared in PR 2/3.
