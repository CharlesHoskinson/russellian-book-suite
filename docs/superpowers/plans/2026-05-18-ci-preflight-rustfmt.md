# CI Preflight Rustfmt Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the fatal GitHub Actions failures from run `26045742623` by making both Rust verifier golden-test files pass `cargo fmt --check` and then verifying the full `make preflight` chain.

**Architecture:** The real failing job is `nix preflight (lint + bake + regression + verifiers)`; `ci required ✓` is only the downstream aggregate gate. `make preflight` stops at the first failing lint command, so the logged CI failure shows Bermuda only, while local probing shows Osmotic has the same rustfmt defect. Make one formatting-only change across both verifier copies, then rerun the same gates CI uses.

**Tech Stack:** GitHub Actions, Nix dev shell, GNU Make, Rust/Cargo/rustfmt, pytest, clj-kondo, ruff, nixpkgs-fmt, npm.

---

## Observed Failure Set

- Fatal in CI: `nix develop -c make preflight` exits during `cargo fmt --check --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml`.
- Fatal if CI advances past the first failure: `cargo fmt --check --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml` has the same diff locally.
- Downstream only: `ci required ✓` prints `one or more required jobs failed` because `preflight` failed.
- Non-fatal noise: `magic-nix-cache-action` logs a FlakeHub authentication error but the step continues with native GitHub Actions cache. Do not bundle this into the rustfmt fix.
- Non-fatal future risk: GitHub warns that Node.js 20 actions are deprecated for `actions/checkout@v4` and `DeterminateSystems/magic-nix-cache-action@v13`. Track separately from this failure fix.

## File Structure

- Modify: `verifiers/bermuda/rust-verifier/tests/golden.rs`
  - Responsibility: Bermuda Rust golden EDN parser tests.
- Modify: `verifiers/osmotic_pressure/rust-verifier/tests/golden.rs`
  - Responsibility: Osmotic Pressure Rust golden EDN parser tests.
- Do not modify: `.github/workflows/ci.yml`
  - The workflow correctly reports the preflight failure. Cache/deprecation warnings are follow-up work.
- Do not modify: `Makefile`
  - The preflight order is useful here because it caught a formatting violation early.

---

### Task 1: Baseline The Formatting Failures

**Files:**
- Read: `verifiers/bermuda/rust-verifier/tests/golden.rs`
- Read: `verifiers/osmotic_pressure/rust-verifier/tests/golden.rs`

- [ ] **Step 1: Confirm the working tree is clean**

Run:

```bash
git status --short --branch
```

Expected: no modified tracked files before starting this task.

- [ ] **Step 2: Reproduce the Bermuda rustfmt failure**

Run:

```bash
cargo fmt --check --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml
```

Expected: FAIL with diffs in `verifiers/bermuda/rust-verifier/tests/golden.rs` around the `expression_atom_value_is_double` and `verdict_status_is_keyword` assertions.

- [ ] **Step 3: Reproduce the Osmotic rustfmt failure**

Run:

```bash
cargo fmt --check --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml
```

Expected: FAIL with the same assertion formatting diffs in `verifiers/osmotic_pressure/rust-verifier/tests/golden.rs`.

---

### Task 2: Apply The Formatting-Only Fix

**Files:**
- Modify: `verifiers/bermuda/rust-verifier/tests/golden.rs`
- Modify: `verifiers/osmotic_pressure/rust-verifier/tests/golden.rs`

- [ ] **Step 1: Let rustfmt rewrite both verifier test files**

Run:

```bash
cargo fmt --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml
cargo fmt --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml
```

Expected: command exits successfully and changes only the two `tests/golden.rs` files.

- [ ] **Step 2: Verify the Bermuda file has this assertion shape**

In `verifiers/bermuda/rust-verifier/tests/golden.rs`, confirm the long assertions are formatted as:

```rust
assert!(
    matches!(value, Edn::Double(_)),
    "expected Double, got {value:?}"
);
```

and:

```rust
assert!(
    matches!(status, Edn::Key(_)),
    "expected Key, got {status:?}"
);
```

- [ ] **Step 3: Verify the Osmotic file has the same assertion shape**

In `verifiers/osmotic_pressure/rust-verifier/tests/golden.rs`, confirm the long assertions are formatted as:

```rust
assert!(
    matches!(value, Edn::Double(_)),
    "expected Double, got {value:?}"
);
```

and:

```rust
assert!(
    matches!(status, Edn::Key(_)),
    "expected Key, got {status:?}"
);
```

- [ ] **Step 4: Inspect the diff for behavior changes**

Run:

```bash
git diff -- verifiers/bermuda/rust-verifier/tests/golden.rs verifiers/osmotic_pressure/rust-verifier/tests/golden.rs
```

Expected: only line wrapping in `assert!` calls. No test logic, fixture paths, or assertions change.

---

### Task 3: Verify The Direct Failure Is Gone

**Files:**
- Test: `verifiers/bermuda/rust-verifier/Cargo.toml`
- Test: `verifiers/osmotic_pressure/rust-verifier/Cargo.toml`

- [ ] **Step 1: Re-run the Bermuda rustfmt check**

Run:

```bash
cargo fmt --check --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml
```

Expected: PASS.

- [ ] **Step 2: Re-run the Osmotic rustfmt check**

Run:

```bash
cargo fmt --check --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml
```

Expected: PASS.

- [ ] **Step 3: Run the local Python support-matrix check**

Run:

```bash
python -m pytest skills/neurosym-forge/tests/test_support_matrix.py -q
```

Expected: `6 passed`.

---

### Task 4: Run The CI Gates In Order

**Files:**
- Test: `Makefile`
- Test: `scripts/ci-steps.txt`
- Test: `.github/workflows/ci.yml`

- [ ] **Step 1: Run the full lint target inside Nix**

Run:

```bash
nix develop -c make lint
```

Expected: PASS for `clj-kondo`, `ruff`, both `cargo fmt --check` commands, `nixpkgs-fmt --check`, and `test_support_matrix.py`.

- [ ] **Step 2: Run scaffold bake inside Nix**

Run:

```bash
nix develop -c make scaffold-bake
```

Expected: PASS or intentional skips only.

- [ ] **Step 3: Run regression inside Nix**

Run:

```bash
nix develop -c make regression
```

Expected: PASS or intentional skips only.

- [ ] **Step 4: Run Bermuda verifier CI inside Nix**

Run:

```bash
nix develop -c make -C verifiers/bermuda ci
```

Expected: `npm install`, `npm run build`, `scripts/extract_preview.py`, and verifier smoke tests complete successfully.

- [ ] **Step 5: Run Osmotic verifier CI inside Nix**

Run:

```bash
nix develop -c make -C verifiers/osmotic_pressure ci
```

Expected: `npm install`, `npm run build`, `scripts/extract_preview.py`, and verifier smoke tests complete successfully.

- [ ] **Step 6: Run the exact top-level preflight command**

Run:

```bash
nix develop -c make preflight
```

Expected: PASS.

---

### Task 5: Commit And Confirm On GitHub Actions

**Files:**
- Commit: `verifiers/bermuda/rust-verifier/tests/golden.rs`
- Commit: `verifiers/osmotic_pressure/rust-verifier/tests/golden.rs`

- [ ] **Step 1: Review tracked changes**

Run:

```bash
git status --short
git diff --stat
```

Expected: exactly two modified Rust test files.

- [ ] **Step 2: Commit the formatting fix**

Run:

```bash
git add verifiers/bermuda/rust-verifier/tests/golden.rs verifiers/osmotic_pressure/rust-verifier/tests/golden.rs
git commit -m "fix: format rust verifier golden tests"
```

Expected: one commit containing only rustfmt output.

- [ ] **Step 3: Push and watch the CI run**

Run:

```bash
git push
gh run watch --repo CharlesHoskinson/russellian-book-suite
```

Expected: `nix preflight (lint + bake + regression + verifiers)`, all `python-skill (...)` jobs, and `ci required ✓` pass.

---

## Follow-Up Work Not Required For This Failure

- FlakeHub cache authentication: decide whether the repository should register/use FlakeHub cache or configure the action to avoid FlakeHub attempts. This is noisy because it emits a GitHub error annotation, but it did not fail this run.
- Node.js 20 action deprecation: update or replace affected actions before GitHub removes Node.js 20 support on September 16, 2026.
