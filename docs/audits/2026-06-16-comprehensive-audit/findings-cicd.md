# Findings — CI / Nix / build

The CI system was overhauled 2026-06-16 (PRs #224/#225). actionlint is **clean (exit 0)**. The prior CI criticals are **all resolved**; what remains is doc/coverage hardening.

## Reconciliation wins (prior CI criticals — all FIXED)

- **Branch-protection drift (prior CRITICAL) — FIXED + guarded.** `scripts/ruleset-apply.sh:40` and `docs/operations/branch-protection.md:12` now require exactly one context, `ci-required` (the ASCII job name at `ci.yml:358`). `scripts/check-required-name.sh` asserts ruleset context == ci.yml job name == literal `ci-required`, wired as the `required-name` flake check in the always-on `lint` job. `merge_group:` trigger present. No merge-wedge risk.
- **Actions pinned to mutable tags (prior) — FIXED.** Every `uses:` across workflows + 3 composite actions is SHA-pinned with a `# vX` comment; dependabot covers the composite-action internals.
- **no-direct-http vacuous contract (prior) — FIXED (replaced).** `ci/.import-linter` demoted to docs-only; real enforcement is `ci/lint_no_direct_http.py` (AST scanner over `skills/*/scripts`), wired via the `invariant-lint` flake check.
- Also fixed: all 4 verifiers have Cargo.lock; dependabot covers all pip/cargo/npm dirs; cargo-test matrix gained adsc-clinical+epidemiology; ci-budget measures execution time + advisory-only + fallback comment; every job has a timeout; OS pinned; `ci.yml` top-level `permissions: contents: read`; ruleset requires 1 approval + last-push approval; nightly `alert-on-failure`.

## Open findings

- **[MEDIUM] `docs/operations/ci-platforms.md:14`** — the platform matrix table says `macos-latest`; `ci.yml` uses pinned `macos-15`. The canonical runbook contradicts the workflow and could mislead a contributor into re-adding a `macos-latest` leg (re-introducing the drift the pin fixed). Fix: update the table to `macos-15`.
- **[MEDIUM] `.github/dependabot.yml:92-95`** — Clojure `deps.edn` CVE scanning is still only a NOTE comment, no job. All 4 verifiers compile/run cljs with deps no scanner covers. Fix: add a nightly clj-watson/clj-holmes job over the 4 `deps.edn` trees; pin coords to exact versions.
- **[MEDIUM] `flake.nix:22-25`** — `x86_64-darwin`/`aarch64-darwin` are declared `supportedSystems` but never `nix flake check`'d by any job (PR checks x86_64-linux; nightly adds aarch64-linux). `toolchains.nix` has darwin-conditional logic (mold linux-only) no leg exercises. A nixpkgs bump breaking darwin eval merges green. Fix: add a nightly `macos-15` `nix flake check` leg, or narrow `supportedSystems` and note darwin best-effort.
- **[LOW] `ci.yml:64-87` (actionlint job)** — actionlint runs without `shellcheck` on PATH (neither locally nor in CI), so inline `run:` shell is never statically linted and the `# shellcheck disable=SC2086` pragmas are inert. Fix: install shellcheck in the actionlint job.
- **[LOW] `ci/compute_matrix.py:114`** — an entry with `"os": []` is silently dropped (zero rows, no error); the empty-*matrix* guard catches zero *total* skills but not one skill contributing zero rows. Latent. Fix: fail closed per-entry on an empty resolved os list.
- **[LOW] `ci/lint_no_direct_http.py:62`** — AST scanner catches only static `import`/`from`; `__import__("requests")`/`importlib.import_module(...)` bypass NFR-4. Low (hygiene guard, not a sandbox). Fix: also flag dynamic-import string literals, or document the static-only scope.
- **[LOW] `verifiers/{epidemiology,adsc-clinical}/Makefile`** — `ci` targets pass vacuously (`echo "...skipping"`, exit 0) when fixtures/tests are absent. Only bites if wired into a gate expecting signal. Fix: fail when expected fixtures are missing.

## Verified-OK (deferred items checked, no finding)

setup-book-python env-indirection (HF ternaries correct); check_windows_canary marker detection (regex + fail-closed guard sound); nightly empty-matrix guard (compute_matrix fails closed on zero selection); npm ci hermeticity (`--no-audit --no-fund`, 3-try backoff, pinned lockfiles); preflight-includes-lint (first preflight target is `lint`); ci-required gating split (`require_success` for always-run vs `require_not_failed` for change-scoped — closes the skipped==pass hole). The cdylib `cargo test` for adsc/epidemiology does run its unit tests (not a silent skip); only the napi-under-test-profile build is worth a one-time confirmation from the #225 run logs.
