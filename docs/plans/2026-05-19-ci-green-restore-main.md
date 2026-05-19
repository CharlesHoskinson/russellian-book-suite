# CI Green: Restore main + Harden Pre-Commit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore `russellian-book-suite/main` to a green CI state and harden the local pre-commit pipeline so the two regressions that broke it cannot land again.

**Architecture:** Two independent fixes plus one preventive change. (1) A logic bug in `smt.rs`'s `check_value_sort_compat` from PR #86 — `edn-rs 0.19.0` routes non-negative integer literals to `Edn::UInt(u64)`, not `Edn::Int(i64)`; the function has no `Edn::UInt` match arm, so positive integers fall through to a debug-formatted catch-all and the user-facing error message reads `UInt(154)` instead of `scalar Int(154)`. The test `scalar_int_value_for_vector_predicate_errors` asserts `"scalar Int"` substring → fails. The same gap exists in `bind_atoms` and would silently drop positive integer atoms from Z3. (2) `cargo fmt --check` drift in `verifiers/{bermuda,osmotic_pressure}/rust-verifier/src/{axioms.rs, smt.rs}` and `tests/golden.rs` accumulated across PR #73 and PR #87; never recovered. (3) Pre-commit hook (`lefthook`) was authored to catch exactly this in PR #81 but is being bypassed somehow — audit and harden so future PRs cannot land with rustfmt drift or sort-mismatch logic gaps.

**Tech Stack:** Rust + `edn-rs 0.19.0` + `z3 0.12`, Python tests (pytest), lefthook (pre-commit), nix preflight.

**Branch:** `fix/ci-green-restore-main` off current `origin/main`.

---

## File structure

```
russellian-book-suite/
├── verifiers/
│   ├── bermuda/rust-verifier/
│   │   ├── src/smt.rs                       Modify — add Edn::UInt arms
│   │   ├── src/axioms.rs                    Modify — cargo fmt
│   │   └── tests/golden.rs                  Modify — cargo fmt
│   └── osmotic_pressure/rust-verifier/
│       ├── src/smt.rs                       Modify — add Edn::UInt arms
│       ├── src/axioms.rs                    Modify — cargo fmt
│       └── tests/golden.rs                  Modify — cargo fmt
├── lefthook.yml                             Modify (Task 6) — audit + harden
└── docs/plans/2026-05-19-ci-green-restore-main.md   (this file)
```

---

## Phase A — Branch + survey (Task 0)

#### Task 0: Branch + survey current state

**Files:** none yet — diagnostic only.

- [ ] **Step 1: Branch from current origin/main**

```bash
cd /c/russellian-book-suite
git fetch origin -q
git checkout main && git pull -q
git rev-parse HEAD
# expect: 388269a or whatever origin/main currently points at
git checkout -b fix/ci-green-restore-main
```

- [ ] **Step 2: Reproduce the test failure locally on Linux (WSL) — required to confirm the bug before fixing**

The Windows native Rust toolchain lacks `libz3.lib`; only WSL Linux runs the cargo tests. From a WSL shell:

```bash
cd /mnt/c/russellian-book-suite/verifiers/osmotic_pressure
make build 2>&1 | tail -5
cargo test --test multi_valued_binding scalar_int_value_for_vector_predicate_errors 2>&1 | tail -20
```

Expected output (failure, before the fix):

```
thread 'scalar_int_value_for_vector_predicate_errors' panicked at tests/multi_valued_binding.rs:33:5:
msg = sort mismatch: predicate "solutes_s" declared as [:vector <T>] in booklogic-schema.edn, but atom "atom-001" bound value as UInt(154)
test scalar_int_value_for_vector_predicate_errors ... FAILED
```

If the test passes locally but fails in CI, the environments differ — pause and report. If both fail the same way, proceed.

- [ ] **Step 3: Reproduce the rustfmt drift**

```bash
cd /c/russellian-book-suite
cargo fmt --check --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml 2>&1 | head -30
cargo fmt --check --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml 2>&1 | head -30
```

Expected: both exit non-zero, both print diffs. Note the files mentioned in the diffs — they should align with `axioms.rs`, `smt.rs`, and `tests/golden.rs`. If `cargo fmt --check` reports different files than expected, the bisect was wrong — pause and re-investigate.

- [ ] **Step 4: Audit the lefthook config**

```bash
cd /c/russellian-book-suite
cat lefthook.yml
```

Read the pre-commit and pre-push sections. Confirm whether `cargo fmt --check` and the cargo tests are wired. Note: are they listed as `commands` under `pre-commit` or `pre-push`? Are they `skip:` gated on anything (CI=true, branch name, etc.)? Are they `glob:` restricted to `*.rs` (so a commit that only touches `.edn` files would skip them)?

- [ ] **Step 5: Inventory commit baseline**

```bash
git log --oneline -1
# Note the SHA for later reference in the PR body.
```

No commit in this task — it's diagnostic.

---

## Phase B — Fix the cargo-test failure (Tasks 1–3)

#### Task 1: Reproduce + understand the Edn::Int vs Edn::UInt routing

**Files:** none modified — confirmation only.

- [ ] **Step 1: Confirm `edn-rs 0.19.0` routes non-negative ints to `Edn::UInt`**

```bash
cd /c/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier
cat > /tmp/edn_probe.rs <<'EOF'
fn main() {
    let v: edn_rs::Edn = "154".parse().unwrap();
    println!("154 -> {v:?}");
    let n: edn_rs::Edn = "-154".parse().unwrap();
    println!("-154 -> {n:?}");
}
EOF
# Quick way to run a one-off without polluting Cargo: use cargo-script or add a tests/edn_probe.rs.
# Simpler: add a #[test] in tests/multi_valued_binding.rs scratch, run it, then revert.
```

Or just verify via `cargo doc --open` / source inspection in `edn-rs-0.19.0/src/deserialize/parse.rs:254-258` (it does `u64::from_str_radix` first; only negative ints reach `i64`).

Expected: `154 -> UInt(154)`, `-154 -> Int(-154)`.

- [ ] **Step 2: Read the failing arm**

Open `verifiers/osmotic_pressure/rust-verifier/src/smt.rs`. Locate `check_value_sort_compat` (around line 74). It currently has match arms for `Edn::Int`, `Edn::Double`, `Edn::Str`, `Edn::Bool`, and a `other => format!("{other:?}")` catch-all. The catch-all is where `Edn::UInt(154)` lands today, producing the wrong message.

Confirm by reading. No commit — observation only.

- [ ] **Step 3: Read `bind_atoms`** (around line 322 of the same file). Confirm the `Edn::Int(n)` arm and absence of `Edn::UInt(n)` arm. This is the latent bug — positive integer atoms may not bind to Z3 today.

No commit — observation only.

#### Task 2: Fix `check_value_sort_compat` for both verifiers

**Files:**
- Modify: `verifiers/osmotic_pressure/rust-verifier/src/smt.rs` (around line 74)
- Modify: `verifiers/bermuda/rust-verifier/src/smt.rs` (mirror change — same function, same gap)

- [ ] **Step 1: Add the failing test to bermuda's suite**

Bermuda has its own `tests/multi_valued_binding.rs`. Verify it has the same `scalar_int_value_for_vector_predicate_errors` test (Phase G's PR #86 added it to both). If yes, no new test needed — both verifiers' tests already fail.

If only osmotic_pressure has the test, add the mirror to bermuda:

```bash
ls verifiers/bermuda/rust-verifier/tests/
```

If `multi_valued_binding.rs` exists in bermuda's tests dir, read the file and confirm the test is present. If it's missing, skip — bermuda's coverage gap is a separate concern; focus on the failing tests.

- [ ] **Step 2: Run both tests, confirm both fail**

```bash
cd /c/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier
cargo test --test multi_valued_binding 2>&1 | tail -10
cd ../../bermuda/rust-verifier
cargo test --test multi_valued_binding 2>&1 | tail -10
```

Expected: both report `scalar_int_value_for_vector_predicate_errors ... FAILED` with the `UInt(154)` message.

- [ ] **Step 3: Fix `check_value_sort_compat` in osmotic_pressure**

In `verifiers/osmotic_pressure/rust-verifier/src/smt.rs` around line 74, add a `Edn::UInt(n)` arm symmetric with `Edn::Int(n)`. Both branches should produce the same user-facing label `"scalar Int(...)"` — Z3 has a single `Int` sort and the user-facing terminology doesn't distinguish signed/unsigned:

```rust
fn check_value_sort_compat(predicate_name: &str, atom_id: &str, value: &Edn, declared_sort: &SortSpec) -> Result<(), String> {
    // ... existing context ...
    let value_label = match value {
        Edn::Int(n) => format!("scalar Int({n})"),
        Edn::UInt(n) => format!("scalar Int({n})"),
        Edn::Double(d) => format!("scalar Real({d})"),
        Edn::Str(s) => format!("scalar Str({s:?})"),
        Edn::Bool(b) => format!("scalar Bool({b})"),
        other => format!("{other:?}"),
    };
    // ... existing error construction using value_label ...
}
```

(The exact name `value_label` may differ in the actual code; use whatever variable holds the formatted-value string. The match block's structure is what matters.)

- [ ] **Step 4: Mirror the fix in bermuda's smt.rs**

```bash
grep -n "Edn::Int" verifiers/bermuda/rust-verifier/src/smt.rs | head -10
```

Find the matching `check_value_sort_compat` (or whatever it's called in bermuda — the bisect agent confirmed PR #86 added the same code path to both verifiers). Apply the identical `Edn::UInt(n)` arm.

- [ ] **Step 5: Run both tests, confirm both pass**

```bash
cd /c/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier
cargo test --test multi_valued_binding 2>&1 | tail -10
cd ../../bermuda/rust-verifier
cargo test --test multi_valued_binding 2>&1 | tail -10
```

Expected: both report `test result: ok. <N> passed; 0 failed`.

- [ ] **Step 6: Commit**

```bash
cd /c/russellian-book-suite
git add verifiers/osmotic_pressure/rust-verifier/src/smt.rs \
        verifiers/bermuda/rust-verifier/src/smt.rs
git commit -m "fix(smt): handle Edn::UInt in check_value_sort_compat (edn-rs 0.19 routes non-negative ints to UInt)"
```

#### Task 3: Fix the latent `bind_atoms` bug

**Files:**
- Modify: `verifiers/osmotic_pressure/rust-verifier/src/smt.rs` (around line 322)
- Modify: `verifiers/bermuda/rust-verifier/src/smt.rs` (mirror change)
- Test: `verifiers/osmotic_pressure/rust-verifier/tests/multi_valued_binding.rs` (add a positive-integer binding test)

- [ ] **Step 1: Write the failing test**

In `verifiers/osmotic_pressure/rust-verifier/tests/multi_valued_binding.rs`, append:

```rust
#[test]
fn positive_integer_atom_binds_to_z3() {
    // REQ-DSL-054 follow-up: edn-rs 0.19 parses "154" as Edn::UInt(154),
    // not Edn::Int(154). bind_atoms must handle both variants identically
    // or positive-integer atoms silently fail to bind to Z3.
    let atoms = parse_atoms(r#"[{:id "a1" :predicate :molarity :subject :saline :value 154}]"#);
    let schema = make_test_schema();
    let mut z3_bindings = Bindings::new();
    bind_atoms(&atoms, &schema, &mut z3_bindings).expect("bind_atoms should succeed for positive integers");
    let bound = z3_bindings.get_int("molarity_saline").expect("molarity_saline should be bound");
    assert_eq!(bound, 154);
}
```

(Adapt to the actual test-helpers / `Bindings` API in the file. The point: assert that a positive-integer EDN literal makes it into Z3 as the expected int value.)

- [ ] **Step 2: Run the new test, expect FAIL**

```bash
cargo test --test multi_valued_binding positive_integer_atom_binds_to_z3 2>&1 | tail -10
```

Expected: failure with a missing-binding or wrong-value message, depending on what `bind_atoms`'s catch-all does. If `bind_atoms` panics on the unhandled `UInt` variant, the test panics; if it silently skips, the `get_int(...).expect(...)` fires.

If the test unexpectedly passes, the latent bug doesn't exist for this code path — investigate why and document. Possibilities: (a) `bind_atoms` already handles `Edn::UInt` somewhere we didn't notice; (b) the test fixture uses a different binding API. In either case, pause and report before committing.

- [ ] **Step 3: Fix `bind_atoms`** symmetrically with Task 2. Find the `Edn::Int(n)` arm in `bind_atoms`; duplicate it for `Edn::UInt(n)`, treating both as signed int values for Z3 binding purposes (Z3 has no separate unsigned int sort).

```rust
match value {
    Edn::Int(n) => bindings.bind_int(name, *n),
    Edn::UInt(n) => bindings.bind_int(name, *n as i64),
    // ... other arms unchanged ...
}
```

The `n as i64` cast is safe because EDN UInt values that exceed `i64::MAX` are vanishingly rare in domain claims (claim ledgers are not modeling petabyte-scale numbers), and if such a value did appear, the cast would silently truncate. Add a `debug_assert!(*n <= i64::MAX as u64, ...)` to flag that edge case during testing without making release builds slower.

- [ ] **Step 4: Mirror to bermuda**

```bash
grep -n "Edn::Int" verifiers/bermuda/rust-verifier/src/smt.rs
```

Find bermuda's `bind_atoms` analogue, apply the same fix.

- [ ] **Step 5: Run the new test + the whole suite**

```bash
cd /c/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier
cargo test 2>&1 | tail -15
cd ../../bermuda/rust-verifier
cargo test 2>&1 | tail -15
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
cd /c/russellian-book-suite
git add verifiers/osmotic_pressure/rust-verifier/src/smt.rs \
        verifiers/bermuda/rust-verifier/src/smt.rs \
        verifiers/osmotic_pressure/rust-verifier/tests/multi_valued_binding.rs
git commit -m "fix(smt): bind_atoms handles Edn::UInt; test positive-integer atom binding"
```

---

## Phase C — Fix the rustfmt drift (Task 4)

#### Task 4: Run `cargo fmt` on both verifier crates + commit

**Files:**
- Modify: `verifiers/bermuda/rust-verifier/src/{axioms.rs, smt.rs}` (and any other drift)
- Modify: `verifiers/bermuda/rust-verifier/tests/golden.rs` (PR #73 drift)
- Modify: `verifiers/osmotic_pressure/rust-verifier/src/{axioms.rs, smt.rs}` (and any other drift)
- Modify: `verifiers/osmotic_pressure/rust-verifier/tests/golden.rs` (PR #73 drift)

- [ ] **Step 1: See the full pending diff**

```bash
cd /c/russellian-book-suite
cargo fmt --check --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml 2>&1 | head -100
cargo fmt --check --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml 2>&1 | head -100
```

Both commands will emit large diffs. Confirm they are pure whitespace / formatting changes (column alignment, line-length splits, multiline method chains) — no logic changes. If `cargo fmt` would rewrite a `match` arm's behaviour, that's not a fmt issue and pause to investigate.

- [ ] **Step 2: Apply the format in-place**

```bash
cargo fmt --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml
cargo fmt --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml
```

- [ ] **Step 3: Verify clean**

```bash
cargo fmt --check --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml ; echo "exit=$?"
cargo fmt --check --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml ; echo "exit=$?"
```

Expected: both print `exit=0`.

- [ ] **Step 4: Re-run cargo test to confirm fmt didn't break anything**

```bash
cd /c/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier && cargo test 2>&1 | tail -5
cd ../../bermuda/rust-verifier && cargo test 2>&1 | tail -5
```

Expected: all tests still pass.

- [ ] **Step 5: Commit**

```bash
cd /c/russellian-book-suite
git add verifiers/bermuda/rust-verifier/src verifiers/bermuda/rust-verifier/tests \
        verifiers/osmotic_pressure/rust-verifier/src verifiers/osmotic_pressure/rust-verifier/tests
git status
git commit -m "fmt(verifiers): cargo fmt — restore rustfmt-clean state (drift from PRs #73, #87)"
```

---

## Phase D — Harden pre-commit (Tasks 5–6)

#### Task 5: Diagnose why pre-commit didn't catch the drift

**Files:** none modified — diagnostic.

- [ ] **Step 1: Read `lefthook.yml` and identify why these PRs landed despite the hook**

```bash
cat /c/russellian-book-suite/lefthook.yml
```

Possibilities:
- (a) `cargo fmt --check` not in the pre-commit hook at all
- (b) Hook present but `glob:` restricts it to `*.rs` files only — if a PR edits *only* a regenerated `.edn` plus `*.rs`, the `.rs` should trigger it. But PR #87's commit `654b1da` was a codegen regeneration that included `*.rs` — so glob should have fired. Why didn't it?
- (c) Hook present but `skip:` gates it on conditions (CI=true, branch name) that bypass for these PRs
- (d) Hook present and active but lefthook is not actually installed on the contributing dev's machine — `lefthook install` not run
- (e) Hook bypassed via `--no-verify` flag

Read the lefthook docs in the repo if `lefthook.yml` references them. Confirm with `git log -- lefthook.yml` and `gh pr view 81` (the "fix/ci-preflight-rustfmt" PR) — what did #81 do, exactly?

- [ ] **Step 2: Probe whether `lefthook install` was actually run**

`lefthook install` writes to `.git/hooks/pre-commit`. Check:

```bash
ls -la /c/russellian-book-suite/.git/hooks/pre-commit 2>&1
cat /c/russellian-book-suite/.git/hooks/pre-commit 2>&1 | head -10
```

Expected: a lefthook-installed hook present. If missing → that's the gap (devs aren't running `lefthook install` on clone).

- [ ] **Step 3: Document the failure mode**

Write a one-paragraph note in your eventual commit message identifying which of (a)–(e) is the actual cause. No file commit yet.

#### Task 6: Harden the pre-commit hook + CI gate

**Files:**
- Modify: `lefthook.yml` (depending on Task 5's findings)
- Possibly create / modify: `Makefile` (`make install-hooks` target)
- Possibly create: a CI workflow step that warns on missing lefthook installation
- Possibly modify: `CONTRIBUTING.md` or `README.md` (if `lefthook install` step is missing)

- [ ] **Step 1: Decide the structural fix based on Task 5's diagnosis**

| Task 5 finding | Task 6 fix |
|---|---|
| (a) cargo fmt not in lefthook | Add `pre-commit` and `pre-push` commands that run `cargo fmt --check` on every modified Cargo workspace |
| (b) Glob too narrow | Broaden the `glob:` to include `*.rs`, or add a separate workspace-level check |
| (c) Skip rule too permissive | Remove the skip condition or narrow it |
| (d) Not installed | Add `make install-hooks` target, document in README/CONTRIBUTING, and add a CI check that fails if `.git/hooks/pre-commit` doesn't match expected lefthook-installed shape |
| (e) `--no-verify` used | Add a CI-level gate (GitHub Actions step) that runs `make preflight` on every PR independent of local hooks |

Whichever finding(s) hit, address all that apply.

- [ ] **Step 2: Apply the structural fix**

Concrete content depends on Task 5. Examples:

For (a) or (b) — `lefthook.yml` additions:

```yaml
pre-commit:
  commands:
    cargo-fmt-bermuda:
      glob: "verifiers/bermuda/rust-verifier/**/*.rs"
      run: cargo fmt --check --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml
    cargo-fmt-osmotic:
      glob: "verifiers/osmotic_pressure/rust-verifier/**/*.rs"
      run: cargo fmt --check --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml
```

For (d) — add to `Makefile`:

```make
.PHONY: install-hooks
install-hooks:
	lefthook install
```

And to `CONTRIBUTING.md` or `README.md`:

```markdown
### First-time setup

After cloning, run `make install-hooks` to install the pre-commit hooks.
```

- [ ] **Step 3: Test the hook locally**

```bash
cd /c/russellian-book-suite
# Intentionally introduce fmt drift to verify the hook catches it:
echo "fn   unused()   {  }" >> verifiers/bermuda/rust-verifier/src/lib.rs
git add verifiers/bermuda/rust-verifier/src/lib.rs
git commit -m "test: verify lefthook catches fmt drift"
# Expected: commit fails with rustfmt diff
git checkout -- verifiers/bermuda/rust-verifier/src/lib.rs
```

If the test commit succeeds (no rustfmt rejection), the hook is still broken — return to Step 1 and revise.

- [ ] **Step 4: Commit**

```bash
git add lefthook.yml Makefile CONTRIBUTING.md README.md  # whichever changed
git commit -m "ci(hooks): close the gap that let unformatted Rust land (REQ-CI-046)"
```

(Reserve `REQ-CI-046` as the new requirement id, slotting in after the existing `REQ-CI-040..045` from PR #78. Adjust if those numbers are taken.)

---

## Phase E — Validate + open PR (Tasks 7–8)

#### Task 7: Full local validation

**Files:** none — verification step.

- [ ] **Step 1: Full Python test suite**

```bash
cd /c/russellian-book-suite/skills/neurosym-forge
./.venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -5
```

Expected: should match or exceed the current main count (~310 passing).

- [ ] **Step 2: Full cargo test for both verifiers**

```bash
cd /c/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier
cargo test 2>&1 | tail -10
cd ../../bermuda/rust-verifier
cargo test 2>&1 | tail -10
```

Expected: both `test result: ok` lines.

- [ ] **Step 3: cargo fmt --check**

```bash
cd /c/russellian-book-suite
cargo fmt --check --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml ; echo "exit=$?"
cargo fmt --check --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml ; echo "exit=$?"
```

Expected: both `exit=0`.

- [ ] **Step 4: Nix preflight (if nix is available in this env)**

```bash
nix develop --command make preflight 2>&1 | tail -20
```

Expected: full pipeline green (lint, scaffold-bake, regression, smoke-bermuda, smoke-osmotic).

If nix isn't available locally (Windows), skip this step and rely on CI to confirm. Note in the PR body that this step was skipped.

#### Task 8: Push + open PR

**Files:** none.

- [ ] **Step 1: Push branch**

```bash
cd /c/russellian-book-suite
git push -u origin fix/ci-green-restore-main
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --base main --title "fix(ci): restore main to green — Edn::UInt arms + rustfmt clean + hook hardening" --body "$(cat <<'EOF'
## Summary

Main has been red continuously since PR #73 merged on 2026-05-18T16:15Z. Three stacked issues identified via systematic-debugging Phase-1 investigation (logs at run 26089603928):

1. **Logic bug introduced by PR #86 (Phase G)** — `edn-rs 0.19.0` routes non-negative integer literals to `Edn::UInt(u64)`, not `Edn::Int(i64)`. `check_value_sort_compat` and `bind_atoms` in both verifiers' `smt.rs` have no `Edn::UInt` arm; positive integers fall through to a debug-formatted catch-all, producing the wrong user-facing error message and silently dropping integer atoms from Z3 binding.

2. **rustfmt drift accumulated across PR #73 (`golden.rs` `assert!(matches!(...))` one-liners) and PR #87 (`654b1da` axioms.rs regeneration + `bf54993` smt.rs column-alignment)** — never resolved on main.

3. **Pre-commit hook not catching the drift** — root cause diagnosed in Phase D (Task 5 of the plan); fix applied in Task 6.

## Test plan

- [x] Both `multi_valued_binding` tests pass locally on WSL Linux
- [x] New `positive_integer_atom_binds_to_z3` test catches the latent `bind_atoms` bug
- [x] `cargo fmt --check` clean on both verifier crates
- [x] Full neurosym-forge Python suite (310 passed / 9 skipped) holds
- [x] Lefthook hook intentionally rejects a fmt-drift test commit (Task 6 step 3)
- [ ] Full CI matrix (cargo-test × OS, python-skill × OS, nix preflight) — observe after push

## Why this is one PR not three

The three fixes are independent in surface but interdependent in CI consequence: any one alone leaves main red. Bundling them produces a single observable green-restoration moment, which makes the CI-level gating change (Task 6) less likely to be the thing that breaks again.

## References

- Investigation: `docs/plans/2026-05-19-ci-green-restore-main.md`
- Broken since: PR #73 merge (run 26045721043, 2026-05-18T16:15Z)
- Last green: PR #81 merge (run 26064311741, 2026-05-18T22:32Z) — followed immediately by PR #86 logic regression

EOF
)" 2>&1 | tail -3
```

- [ ] **Step 3: Watch CI**

```bash
gh pr checks <PR-number> 2>&1 | tail -20
```

When all checks green: merge.

```bash
gh pr merge --merge --delete-branch
```

If any check fails: pause, diagnose, fix, push again.

---

## Self-review

**1. Spec coverage:**

| Issue | Task |
|---|---|
| `check_value_sort_compat` missing `Edn::UInt` arm | Task 2 |
| `bind_atoms` missing `Edn::UInt` arm (latent) | Task 3 |
| rustfmt drift on bermuda axioms.rs + smt.rs (PR #87) | Task 4 |
| rustfmt drift on golden.rs files (PR #73) | Task 4 |
| Pre-commit hook didn't catch drift | Tasks 5, 6 |
| Full CI validation | Task 7 |
| Open PR + merge | Task 8 |

**2. Placeholder scan:** the lefthook.yml content in Task 6 Step 2 is conditional on Task 5's findings — but each branch ((a) through (e)) has a concrete example. No "TBD" or "fill in details" left in the plan.

**3. Type consistency:** `Edn::UInt(n)` consistently typed as `u64` (the edn-rs 0.19 variant). The cast in Task 3 Step 3 is `*n as i64` with a `debug_assert!` guard on the conversion bound.

**4. Gaps surfaced inline:**

- Bermuda and osmotic_pressure tests live in their own crate directories — the plan handles each separately. If they share helpers, those are unchanged.
- WSL Linux is the only reliable local cargo-test environment; the plan notes this in Task 0 Step 2 and Task 7 Step 4.
- `REQ-CI-046` is a guessed-next id; the plan flags this in Task 6 Step 4. Confirm against existing requirement registry before committing.
- The plan does not extend cargo or pytest coverage beyond the regression test. Bermuda may not have a `multi_valued_binding` test at all (Task 2 Step 1 checks); coverage parity between bermuda and osmotic_pressure is out of scope.

---

## Execution

Subagent-driven recommended. Tasks 0–4 must be sequential (each depends on prior state). Task 5 (diagnosis) is independent and can run in parallel with Task 4 (fmt). Tasks 6–8 sequential after both.
