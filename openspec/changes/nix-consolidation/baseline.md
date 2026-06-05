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
