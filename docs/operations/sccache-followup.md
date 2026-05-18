# sccache re-enable runbook

## Status

`sccache` is **disabled** as of the ci-cleanup mission (PR-65, 2026-05-18).
Build caching relies on `Swatinem/rust-cache@v2` (caches `target/`) +
`DeterminateSystems/magic-nix-cache-action@v13` (caches Nix store).

## Why it's off

In a `nix preflight` job running both `Swatinem/rust-cache` and
`magic-nix-cache`, the `mozilla-actions/sccache-action@v0.0.7` step crashes
during cargo build:

```
sccache: error: Server startup failed: create gha cache failed:
ConfigInvalid (permanent) at => cache url for ghac not found,
maybe not in github action environment?
```

When multiple cache layers compete for the same GitHub Actions Cache API
namespace, opendal's GHAC backend hits per-route rate limits and returns
`Twirp ResourceExhausted: rate limit exceeded`. sccache then panics inside
`opendal::services::ghac::core::GhacCore::ghac_get_download_url`, cargo
build aborts with exit 101, and the entire preflight job dies.

The bug surfaces only when:
1. Multiple GHA Cache consumers run in the same job (Swatinem +
   magic-nix-cache + sccache), AND
2. The cache backend hits a transient throttle (high org traffic, or a
   recent commit-storm on the repo).

It does not surface in isolation. A standalone job using only
`sccache-action` would work; so would a Nix-only or Swatinem-only job.

## What "re-enabled" looks like

There are three reasonable re-enable paths, in order of investment:

### Option A — Cachix instead of magic-nix-cache

Move Nix store caching to Cachix (S3-backed, no GHA Cache contention). Then
re-add `sccache-action` to the preflight job; sccache + Swatinem then share
GHA Cache between just two consumers.

Cost: one-time Cachix org/cache setup, monthly fee, `CACHIX_AUTH_TOKEN`
secret on the repo. Yields the original goal (Nix-store cache + per-CU
cargo cache + target/ cache).

```yaml
# Replace magic-nix-cache with:
- uses: cachix/cachix-action@v15
  with:
    name: russellian-book-suite
    authToken: ${{ secrets.CACHIX_AUTH_TOKEN }}
# Then re-add:
- uses: mozilla-actions/sccache-action@v0.0.7
- run: nix develop -c make preflight
  env:
    RUSTC_WRAPPER: sccache
    SCCACHE_GHA_ENABLED: "true"
```

### Option B — sccache with S3 backend

Stand up an S3 bucket (or any S3-compatible store like Cloudflare R2). Point
sccache at it via `SCCACHE_BUCKET`/`SCCACHE_S3_KEY_PREFIX`. Independent of
GHA Cache entirely.

Cost: cloud bucket + credentials secret. Cache hits cross-runs (unlike GHA
Cache which is per-branch).

### Option C — leave sccache off (current state)

Accept ~10-20% slower incremental cargo builds. Swatinem already saves the
heavy `target/` directory between runs, so the marginal benefit of
per-compilation-unit caching is modest for our two small verifier crates
(~30 deps each, mostly z3/edn-rs/napi).

This is the path of least friction unless CI wall-time becomes a problem
the existing caches can't address.

## How to verify after re-enabling

1. Push the re-enable PR to a branch.
2. Watch the preflight job for the `sccache: error: Server startup failed`
   pattern. If it appears, the contention is still present and the
   re-enable approach you chose is insufficient.
3. Compare wall-time of the preflight job before/after across at least 5
   PRs. Less than 10% improvement = the cost of the sccache infrastructure
   isn't paying off; consider Option C instead.

## Related artifacts

- `.github/workflows/ci.yml` — preflight job; `RUSTC_WRAPPER` env was
  removed at the workflow level in commit `eda80f8`. The flake's shellHook
  was simultaneously updated to stop setting it unconditionally.
- `flake.nix` — `devShells.default.shellHook` no longer sets
  `RUSTC_WRAPPER=sccache`. Restore that line when re-enabling.
- Reference: [sccache + GHA Cache contention thread](https://github.com/mozilla/sccache/issues?q=ghac+ConfigInvalid)
