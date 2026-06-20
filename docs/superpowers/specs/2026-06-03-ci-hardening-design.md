# CI hardening — design

**Date:** 2026-06-03
**Context:** The carve-completion arc (specs/2026-06-03-carve-completion-design.md) surfaced four CI defects under load: a HuggingFace download flake hit four PRs in one day (#192, #194, #197, #203), a zero-marked skill reddened `ci-required` repo-wide (#195's root cause), a 47-PR dependabot flood queued ~12 hours of redundant jobs, and the setup-python composite pin runs on node20 with GitHub's forced node24 switch landing June 16, 2026.

## Root causes

1. **HF flake.** `SentenceTransformer("all-MiniLM-L6-v2")` revalidates its cache with HEAD requests per model file on every load. neurosym-forge's pytest runs under xdist `-n auto`; parallel workers each load the model → HEAD storm → HF Hub 429 → huggingface_hub retry exhaustion → `EmbeddingUnavailableError` → semantic-index tests fail (or the download hangs → job cancellation). CI persists no HF cache and never sets `HF_HUB_OFFLINE`. The spaCy model in the same workflow already has the correct pattern: pinned artifact + `actions/cache` + retry-wrapped fetch.
2. **Canary gap.** The Windows matrix leg runs `pytest -m windows_canary` unconditionally. A matrix skill with zero marked tests exits 5 (no tests collected) and fails `ci-required` on every PR. Nightly `windows-full-canary` catches under-tagging, but nothing catches zero-tagging at PR time.
3. **Queue saturation.** `python-skill-matrix` (35 jobs) runs unconditionally — verifier-only and docs-only PRs pay the full matrix. The `rust` path filter is over-broad: `skills/**` triggers `cargo-test`, which compiles only verifier crates.
4. **node24 deadline.** `.github/actions/setup-book-python` pins `actions/setup-python` v5.6.0 (node20). Dependabot's `github-actions` entry does not scan this composite's internals. `ci-legacy.yml` already uses v6.2.0.

## Fixes

**F1 — HF model cache + offline mode.** For neurosym-forge matrix legs (the only legs installing the `semantic` extra): `actions/cache` on the HuggingFace hub cache directory keyed `hf-model-all-MiniLM-L6-v2-v1`; a warmup step that, when the model is absent, runs a retry-wrapped single-process `huggingface_hub.snapshot_download("sentence-transformers/all-MiniLM-L6-v2")`; pytest then runs with `HF_HUB_OFFLINE=1`, which skips HEAD revalidation entirely (huggingface_hub resolves from the local `refs/main` snapshot). Apply the identical pattern to `nightly-flake-drift.yml`'s neurosym-forge row and `ci-legacy.yml`'s `test-neurosym-forge` if it installs `semantic`. Cache path is OS-dependent (`~/.cache/huggingface` on Linux/macOS, `~\.cache\huggingface` resolved via `HF_HOME` set explicitly to a workspace-relative dir to keep one cross-OS path).

**F2 — canary zero-marking guard.** New `ci/check_windows_canary.py`, run as a step in the existing `lint` job: parse `.github/workflows/ci.yml`, derive the python-skill matrix rows that run full pytest on Windows (skill axis minus `smoke: import` rows), and fail with a named-skill, named-fix message if a skill's `tests/` contains no `windows_canary` marker. Stdlib-only (regex/YAML-lite parsing acceptable; the matrix block is structured enough for a targeted parse — if `pyyaml` is available in the lint venv, use it).

**F3 — path-gate the python matrix; narrow cargo.** Extend the `changes` job with a `python` filter: `skills/**`, `sibling_skills/**`, `.github/workflows/ci.yml`, `.github/actions/setup-book-python/**`, `ci/**`. Gate `python-skill-matrix` with `if: github.event_name == 'push' || needs.changes.outputs.python == 'true'`. Narrow the `rust` filter to `verifiers/**`, `**/*.rs`, `**/Cargo.toml`, `**/Cargo.lock`, `flake.nix`, `flake.lock`, `Makefile`, `.github/workflows/ci.yml` — dropping `skills/**`, `tools/**`, and the interpreted-language globs whose verifier copies already live under `verifiers/**`. `preflight` keeps a broad trigger (`python OR rust` outputs) because `make preflight` spans both worlds. In `required`, move `python-skill-matrix` from `require_success` to `require_not_failed` (same treatment as preflight/cargo-test; skipped-by-filter is legitimate). `lint`, `actionlint`, `ci-divergence-summary` stay `require_success` — `ci-divergence-summary` must tolerate skipped upstreams (verify its `if: always()` logic handles skipped needs).

**F4 — node24.** Bump the composite's `setup-python` pin to v6.2.0 (`a309ff8b426b58ec0e2a45f0f869d46889d02405`, the SHA `ci-legacy.yml` already trusts). Add a dependabot `github-actions` entry with `directory: /.github/actions/setup-book-python` so the composite's pins are scanned weekly.

**F5 — documentation only.** Comment at the `concurrency:` block: queued (not running) main runs are superseded by newer pushes by design; cancelled main runs after rapid sequential merges are expected, and the newest run validates the cumulative tree.

## Verification

- F1: PR's own neurosym-forge legs run green; the warmup step shows a cache hit on the second run (re-run the leg once to observe). Grep job logs for `HTTP Error 429` — must be absent.
- F2: the guard passes on main as-is; mutation test during development — temporarily strip markers from one skill locally and confirm the script fails with the named skill.
- F3: the PR itself (touching `.github/**` + `ci/**`) runs the full matrix. After merge, observe a docs-only or verifier-only PR skipping the python matrix with `ci-required` green. Risk gate: `required`-job aggregation reviewed line-by-line; branch protection hangs off it.
- F4: composite action runs on node24 (job log header shows the runtime); no behavior change expected.

## Out of scope

- Per-skill dynamic matrix gating (`fromJSON` matrices) — coarse gating already kills the observed flood; revisit only if skill-level PRs become the bottleneck.
- rayon/graph_builder unpin — tracked by the ignore comment in dependabot.yml; upstream's move.
- Runner concurrency/plan changes; merge queues.

## Rollout

One PR (`ci/hardening`), one commit per fix, F1→F5 order. The PR's own CI run exercises F1 and F3 directly. Same QA-gate discipline as the carve arc: read-only auditor before push, post-merge verification after.
