# nix-consolidation baselines

Pre-arc wall times, from run 27023375152 (main @ 408f9bd, the #213 merge —
last green main run on the magic-nix-cache layer):

| Job | Wall time |
|---|---|
| lint | 178s |
| nix preflight (lint + bake + regression + verifiers) | 469s |
| cargo-test, slowest leg (bermuda / macos-15) | 172s |
| cargo-test, fastest leg (osmotic_pressure / ubuntu-24.04) | 107s |
| actionlint | 7s |

Cache layer at baseline: magic-nix-cache (deprecated). Post-PR numbers
appended below per PR.

## After PR 2 (run 27030180304, nix/consolidation-pr2 @ 8dd28e9)

Cold nix store for the new `nix/**`-keyed cache entry — warm runs improve on
these.

| Job | Baseline | PR 2 |
|---|---|---|
| lint | 178s | 132s (one `nix flake check -L`, replaces 4 steps) |
| nix preflight | 469s | 444s (lint double-run gone) |
| cargo-test bermuda/macos-15 | 172s | 127s (job unchanged until PR 3; runner noise) |

## Arc close-out (after PR 3 #216 + hotfix #217)

Warm-cache numbers from the #217 validation run (27039822539) and its
cargo legs:

| Job | Baseline | Final |
|---|---|---|
| lint | 178s | 102s (warm store, 8G GC budget) |
| nix preflight | 469s | 155s (warm store; suites only) |
| cargo-test linux legs | 107-109s | 110-115s (parity; cold-ish rust-shell store) |
| cargo-test macos legs | 132-172s (brew) | 322-326s (COLD store save run) |
| nightly flake-check-arm | — | first run green (aarch64-linux now actually built) |

The macOS cargo numbers above are the cold-store run that also paid the
cache save. The design's revert criterion (brew on macOS only) applies to
WARM runs — measured on the next rust-touching PR; if warm macOS stays
materially above the brew baseline, apply the revert path from design.md §7.

Hotfix #217 en route: mold is marked broken on darwin in nixpkgs 25.05;
the cargo legs were the first CI consumers of the rust shell on macOS.
mold + its linker flag + the z3 LD_LIBRARY_PATH export are now
linux-gated.
