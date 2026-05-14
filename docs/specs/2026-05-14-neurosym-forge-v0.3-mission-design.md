# neurosym-forge v0.3 mission — Design

Date: 2026-05-14
Author: Charles
Status: Draft, pending user approval

## Problem

`neurosym-forge` v0.2 shipped with PR #14 + PR #18: scaffolder, EDN-as-Atomspace IR, Bermuda predicate map, canonical-facts axioms in `canonical.rs`, book-qa D13 hook. The structure is end-to-end, but three properties are unproven:

1. **The Rust addon does not actually verify anything.** The scaffolded `smt.rs` returns `Sat` regardless of input; `ir.rs::parse_formulas` returns `Ok(Vec::new())`; `canonical.rs::assert_bermuda_axioms` is never called from `check_all`. A live `npm run verify` against Bermuda would always report `:sat` even when the ch-02 prose says "8 parishes" against the canonical 9. The verifier is a structural placeholder, not a working verifier.

2. **The scaffold is not domain-agnostic in practice.** Only one project was ever scaffolded (`verifiers/bermuda/`). Whether `neurosym-forge` actually produces a working verifier for a non-book domain — chemistry, legal, math — is untested.

3. **Predicate-map evolution is undocumented.** Bermuda ships with five predicates frozen at scaffold time. Whether the workflow for adding a sixth predicate (regex pattern + Z3 axiom) is ergonomic or painful is untested.

Plus three skill-level usability issues surfaced during PR #18 implementation:

- The scaffolded `Cargo.toml` requires `tectonic`, which requires `libpng` + `pkg-config`, which is not installed on a stock Windows or many Linux dev machines. The Rust addon cannot build for any project unless the user installs system libraries — and tectonic is only needed for `render_pdf`, not for `verify_formulas`.
- The `--out` flag rejects `..` segments outright (PR #14's security fix); legitimate uses like `--out ../../verifiers/bermuda` from `skills/neurosym-forge/` fail.
- Adding a predicate today means touching `rules/predicates.edn` (regex), `scripts/ingest_ledger.py` (predicate map application), and `rust-verifier/src/canonical.rs` (Z3 axiom). No single source of truth.

## Mission

Prove neurosym-forge works correctly across three real uses, fixing skill gaps as they surface. Deliverables:

- **D1.** A live Bermuda verification that flags the ch-02 parish-count drift as a critical D13 ticket via real Z3 (no stub).
- **D2.** A scaffolded `verifiers/osmotic_pressure/` that runs a non-book chemistry verification, demonstrating the scaffold is generic.
- **D3.** An expanded Bermuda predicate map covering four quantitative claims (population, land area, GDP, hospital beds), with the workflow for adding predicates documented in operating notes.

Each deliverable surfaces specific neurosym-forge improvements; those improvements land in v0.3 so future scaffolded projects inherit them.

## Three-PR slate

The mission decomposes into three sequential PRs. Each is independently reviewable; each unblocks the next.

```
            ┌────────────────────────────────┐
            │  PR-1 — neurosym-forge v0.3    │
            │  hardening                      │
            │                                 │
            │  • tectonic feature-gated       │
            │  • ir.rs+smt.rs templates real  │
            │  • --out .. policy relaxed      │
            │  • new tests for the verify path │
            └─────────────────┬──────────────┘
                              │ unblocks
                              ▼
            ┌────────────────────────────────┐
            │  PR-2 — Bermuda real run +     │
            │  predicate expansion           │
            │                                 │
            │  • build Rust addon (no tectonic)│
            │  • wire canonical.rs ↔ smt.rs   │
            │  • parse atoms; run real Z3     │
            │  • ch-02 drift → D13 critical   │
            │  • +4 quantitative predicates    │
            │  • verification-report v0.2     │
            └─────────────────┬──────────────┘
                              │ confirms genericity
                              ▼
            ┌────────────────────────────────┐
            │  PR-3 — Second workspace       │
            │  (osmotic-pressure)            │
            │                                 │
            │  • scaffold verifiers/...      │
            │  • encode van 't Hoff (i=2)     │
            │  • verify sat on clean ledger   │
            │  • verify unsat on doctored i=1 │
            └────────────────────────────────┘
```

Between PRs the controller comes back to brainstorming to re-plan based on what landed (new failures, scope adjustments, surprises). This spec is the strategic doc; each PR gets its own tactical plan via writing-plans.

## PR-1 detail — neurosym-forge v0.3 hardening

### Goal

Make the scaffolded Rust addon actually capable of verifying. Today every scaffolded project ships stubs that return `Sat` regardless of input. After PR-1, a freshly-scaffolded project's Rust side reads atoms via serde-json, asserts canonical-axioms (if a `canonical.rs` is present), tracks each non-axiom atom for unsat-core membership, and returns a real Z3 verdict.

### Changes

#### Tectonic feature flag

In `assets/project-template/rust-verifier/Cargo.toml.tmpl`:

```toml
[features]
default = ["smt", "eqsat", "kg"]
smt   = ["dep:z3"]
eqsat = ["dep:egg"]
kg    = ["dep:cozo"]
pdf   = ["dep:tectonic"]

[dependencies]
napi        = { version = "3", features = ["napi9", "serde-json", "async"] }
napi-derive = "3"
serde       = { version = "1", features = ["derive"] }
serde_json  = "1"
thiserror   = "2"
z3          = { version = "0.20", features = ["bundled"], optional = true }
egg         = { version = "0.10", optional = true }
cozo        = { version = "0.7", default-features = false, features = ["compact"], optional = true }
tectonic    = { version = "0.16", optional = true }
```

In `lib.rs.tmpl`, gate the `render_pdf` napi entry point under `#[cfg(feature = "pdf")]` so a non-pdf build does not export it.

In `typeset.rs.tmpl`, gate the entire module: `#[cfg(feature = "pdf")] mod typeset;` in `lib.rs`.

Users who want PDF rendering: `cargo build --release --features pdf`. Default build skips it.

#### Real `ir.rs.tmpl`

Replace the stub `parse_formulas` with a serde-json walker that consumes the EDN-as-JSON format the Python ingester emits:

```rust
pub fn parse_formulas(edn: &str) -> Result<Vec<(ClaimId, Atom)>, Error> {
    let parsed: serde_json::Value = serde_json::from_str(edn)
        .map_err(|e| Error::Parse(e.to_string()))?;
    let atoms = parsed.get("atoms")
        .and_then(|v| v.as_array())
        .ok_or_else(|| Error::Parse("missing atoms array".into()))?;
    let mut out = Vec::with_capacity(atoms.len());
    for a in atoms {
        let id = a.get("id").and_then(|v| v.as_str()).unwrap_or("?").to_string();
        out.push((id, a.clone()));
    }
    Ok(out)
}
```

`Atom` becomes `serde_json::Value` (typed dispatch happens in `smt.rs`).

#### Real `smt.rs.tmpl`

Replace the stub with code that:

1. Builds a Z3 `Context` and `Solver`.
2. Calls a project-local hook `assert_axioms(&ctx, &solver)` if present — the scaffold ships this as a no-op stub at `src/axioms.rs`; project-specific work (like `canonical.rs` in Bermuda) replaces or extends it.
3. For each atom from `parse_formulas`, dispatches on the atom's `predicate` field:
   - For `value_kind = int`: builds a Z3 `Int` constant named `predicate_subject`, asserts equality with the value, wraps in `assert_and_track` with the atom's `id`.
   - Same for `bool`, `string`.
   - `:CONTEXT` and `:OPAQUE` atoms are skipped (provenance-only).
4. Calls `solver.check()`; on `Sat` returns the verdict; on `Unsat` extracts the unsat core (by tracker IDs) into `Verdict::core`.

The scaffold emits a generic `smt.rs.tmpl` with this structure. The Bermuda-specific `canonical.rs` already exists from PR #18; PR-2 wires it into `smt.rs::assert_axioms`.

The new `axioms.rs.tmpl` (no-op default):

```rust
//! Project-specific axioms. Override this file (or replace with `canonical.rs`)
//! to assert hard constraints before the per-atom tracked assertions.
use z3::{Context, Solver};

pub fn assert_axioms(_ctx: &Context, _solver: &Solver) {
    // No-op default. Domain-specific verifiers replace this body.
}
```

In `lib.rs.tmpl`, add `mod axioms;` next to the other mod declarations; `smt.rs` calls `crate::axioms::assert_axioms(&ctx, &solver)` at the start of `check_all`.

#### `--out` policy relaxation

In `scripts/scaffold_project.py`, replace the blanket `..` rejection with:

```python
out_str = str(out_dir)
resolved = Path(out_str).resolve()
cwd = Path.cwd().resolve()
if not resolved.is_relative_to(cwd) and not Path(out_str).is_absolute():
    raise ValueError(
        f"--out {out_str!r} resolves outside the current working directory; "
        "use an absolute path if this is intentional"
    )
out_dir = resolved
```

The current check `".." in Path(out_str).parts` blocks `--out ../../verifiers/foo` even when the resolved path stays under the working tree. The new check allows relative paths with `..` segments as long as the resolved path is under `cwd`; absolute paths anywhere are permitted (operator opt-in).

#### New tests

In `skills/neurosym-forge/tests/test_scaffold_project.py`:

- `test_relative_dotdot_under_cwd_accepted` — scaffolding to `tmp_path / ".." / sibling / project` succeeds when `sibling` is under tmp_path's parent and that parent is the cwd.
- `test_absolute_outside_cwd_accepted` — absolute path outside cwd succeeds.
- `test_relative_dotdot_escaping_cwd_rejected` — `--out ../../../../escape` from a deeply-nested cwd is rejected.

In a new file `skills/neurosym-forge/tests/test_rust_template_shape.py`:

- `test_smt_template_calls_axioms_hook` — read `assets/project-template/rust-verifier/src/smt.rs.tmpl`; assert it contains `crate::axioms::assert_axioms`.
- `test_smt_template_uses_assert_and_track` — assert template contains `assert_and_track` (proves unsat-core flow exists).
- `test_axioms_template_is_no_op` — read `axioms.rs.tmpl`; assert it contains an empty function body.
- `test_lib_template_pdf_is_feature_gated` — read `lib.rs.tmpl`; assert `#[cfg(feature = "pdf")]` precedes `render_pdf`.
- `test_cargo_template_has_feature_flags` — read `Cargo.toml.tmpl`; assert `[features]` section exists with `default`, `pdf`, `smt`.

These template-shape tests are cheap (string searches in template files) and catch template drift without requiring Rust to build.

### Out of scope for PR-1

- Actually running cargo build (deferred to PR-2 against Bermuda)
- Replacing the Python ingester with a Rust ingester (still calls into Python)
- WASM target, cvc5 second solver

### Effort

1.5–2 days.

## PR-2 detail — Bermuda real run + predicate expansion

### Goal

Land a real Z3 verification against Bermuda v6.0.0 that fires `:unsat` with the ch-02 parish-count atom in the unsat core. Document the run in a fresh `verification-report.md v0.2`. Extend the Bermuda predicate map with four quantitative claims and re-verify; expect either `:sat` (if chapters are clean on those metrics) or `:unsat` (surfacing new drift).

### Sub-PR-2.1: wire Bermuda's `canonical.rs` into `smt.rs`

After PR-1 lands, the scaffolded `smt.rs` calls `axioms::assert_axioms`. Bermuda already has `canonical.rs` from PR #18. Wiring:

- Rename `canonical.rs` → `axioms.rs` (so it satisfies the v0.3 contract), OR
- Keep `canonical.rs` and add a one-line `axioms.rs` that re-exports: `pub use crate::canonical::assert_bermuda_axioms as assert_axioms;`

Choice: keep `canonical.rs` named (it's domain-meaningful) and add the thin re-export shim. The re-export pattern is the documented way for projects to plug into the scaffold's hook.

`canonical.rs::assert_tracked_atom` already handles serde-json int/string/bool dispatch. Wire it from `smt.rs::check_all` so every ingested atom from `work/claims.edn` and `work/prose-facts.edn` becomes a tracked assertion.

### Sub-PR-2.2: build the addon and run real verify

```bash
cd verifiers/bermuda
.venv/Scripts/python.exe -m scripts.ingest_ledger \
    --ledger ../../examples/bermuda-manual/claims/ledger.jsonl \
    --predicates rules/predicates.edn --out work/claims.edn

.venv/Scripts/python.exe -m scripts.extract_prose \
    --bundles ../../examples/bermuda-manual/book/releases/6.0.0/chapter-bundles \
    --out work/prose-facts.edn

cd rust-verifier && cargo build --release --no-default-features --features smt,kg
cd .. && npm install && npm run build:cljs

.venv/Scripts/python.exe -m scripts.run_verification \
    --workspace ../../examples/bermuda-manual --release 6.0.0
```

Expected outcome: `:unsat` with one of:
- `prose-ch-02-NNN` (the ch-02 "8 parishes" atom)
- `clm-2026-000008` (the ledger atom asserting 9 parishes)

…in the unsat core. The verdict.edn is translated into `examples/bermuda-manual/qa/verification-defects.json` by `verdict_to_qa.py`; book-qa's D13 then fires one critical defect ticket.

### Sub-PR-2.3: extend the predicate map

Add four quantitative claims:

| Predicate | Canonical value | Source | Z3 axiom |
|---|---|---|---|
| `:population` | 64,000 | Bermuda Statistics Department, mid-2024 estimate | `Int = 64000` |
| `:land-area-km2` | 53 | OST gazette | `Int = 53` |
| `:gdp-usd-billion` | 7 | Bermuda Monetary Authority 2023 | `Int = 7` |
| `:hospital-beds-kemh` | 150 | KEMH 2024 annual report | `Int = 150` |

Workflow:
1. Append new claim rows to `examples/bermuda-manual/claims/ledger.jsonl` (append-only per book-knowledge convention).
2. Add patterns to `rules/predicates.edn`.
3. Add Z3 axioms in `canonical.rs::assert_bermuda_axioms`.
4. Re-run the pipeline. Expect `:sat` if chapter prose matches these values; expect `:unsat` per quantitative drift discovered.

Document the **workflow** explicitly in `verifiers/bermuda/docs/adding-a-predicate.md` (5-step recipe).

### Sub-PR-2.4: verification-report v0.2

Overwrite `examples/bermuda-manual/reports/verification-report.md` with:

- The actual verdict (`:sat` or `:unsat`).
- For `:unsat`: the unsat core, the offending claims, and recommended fixes.
- For `:sat`: claim counts, predicate coverage, time taken.
- The new quantitative predicates and what they caught (or didn't).
- Build environment notes (Rust version, Z3 version, feature flags used).

### Effort

2-3 days. The long pole is making `cargo build --features smt,kg` actually succeed — z3.rs bundled mode requires cmake + a C++ toolchain. If the build does not succeed on this machine, the fallback is to run via GitHub Actions on ubuntu-latest (already used for the existing smoke CI job).

## PR-3 detail — second workspace (osmotic-pressure)

### Goal

Prove `neurosym-forge` scaffolds a working verifier for a non-book chemistry domain. The osmotic-pressure example from `skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md` provides the spec; PR-3 turns it into a real `verifiers/osmotic_pressure/` project.

### Changes

1. Scaffold `verifiers/osmotic_pressure/` with `--book-knowledge-bridge` (the bridge will be vestigial since this is not a book workspace; that's fine — exercises the scaffold path).
2. Write `verifiers/osmotic_pressure/rules/predicates.edn` for `:osmotic-pressure-pa`, `:vant-hoff-i`, `:molarity`, `:temperature-k`.
3. Write `verifiers/osmotic_pressure/rust-verifier/src/axioms.rs` asserting the van 't Hoff identity as a soft constraint: `osmotic_pressure ≈ i · M · R · T` (with a 3% tolerance, since the paper's 7.7 atm has rounding error vs the computed 7.53 atm).
4. Write a small fixture `claims_clean.jsonl` (i=2, NaCl) → verify expects `:sat`.
5. Write `claims_doctored.jsonl` (i=1, same NaCl, same pressure) → verify expects `:unsat` because the law cannot be satisfied with i=1.
6. CI smoke job runs both fixtures and asserts the verdicts.

This is largely a tracking-and-glue task. The hard work (Rust verify path) is already shipped by PR-1.

### Effort

1-2 days.

## Cross-cutting verification

For each PR:

- **PR-1**: 71 + new tests pass; `cargo check --no-default-features --features smt` on the scaffolded osmotic-pressure project (via fresh `tmp_path` scaffold in a test) succeeds; template-shape tests catch all template changes.
- **PR-2**: real verification report shows `:unsat` with ch-02 drift atom in core; book-qa's D13 emits a critical ticket; the four new quantitative predicates are documented and at least one is checked against chapter prose.
- **PR-3**: scaffold + verify produces `:sat` on `claims_clean.jsonl` and `:unsat` on `claims_doctored.jsonl`; no Bermuda-specific assumption leaks into the scaffolded osmotic-pressure project.

## Workspace mutation policy

- PR-1 only touches `skills/neurosym-forge/`.
- PR-2 touches `verifiers/bermuda/`, `examples/bermuda-manual/claims/ledger.jsonl` (append-only), `examples/bermuda-manual/reports/verification-report.md`, `examples/bermuda-manual/qa/verification-defects.json` (the verifier writes this; consistent with the v0.2 external-tool carve-out for `qa/`).
- PR-3 touches `verifiers/osmotic_pressure/` and adds a CI job referencing it.

No skill ownership boundaries are crossed; book-knowledge still owns `claims/` but accepts append-only new rows for the four quantitative claims (these are new claim_ids, no transitions on existing rows).

## Non-goals

- WASM build of the Rust verifier (still v0.4)
- cvc5 second-opinion solver (still v0.4)
- Verifier-driven entailment with book-thesis (still v0.4)
- Automatic chapter regeneration loop on D13 fire (still v0.4 — the healer triages but does not re-run the verifier in this cycle)
- Adding non-Bermuda book workspaces (the genericity proof comes from PR-3's chemistry domain, not from another book)

## Workflow between PRs

After PR-1 merges to main, the controller re-enters brainstorming with PR-1's outcomes in hand. Two things commonly happen:

1. **PR-1 surfaces a gap not predicted in this spec.** The PR-2 plan adapts.
2. **PR-1 ships with a deliberate simplification** (e.g., `axioms.rs` is a no-op stub instead of a more clever hook). The PR-2 plan extends rather than overrides.

Same after PR-2 merges. The PR-3 plan is the smallest and most mechanical; it largely consumes what PR-1 + PR-2 produced.

If at any point a PR exposes a fundamental design flaw (e.g., the EDN-as-JSON IR turns out to be a poor fit for Z3 quantifier patterns), the controller pauses, returns to brainstorming with the user, and revises this umbrella spec.

## Estimated effort total

- PR-1: 1.5–2 days
- PR-2: 2–3 days
- PR-3: 1–2 days

**Total: 4.5–7 days** spread across three reviewable PRs.

## Deliverables

1. `docs/specs/2026-05-14-neurosym-forge-v0.3-mission-design.md` (this file).
2. `docs/plans/2026-05-14-neurosym-forge-v0.3-pr1.md` (next; PR-1 only).
3. PR-1 merged: `skills/neurosym-forge/` v0.3.
4. (After PR-1 lands) `docs/plans/2026-05-15-bermuda-real-run-pr2.md` and the merged PR.
5. (After PR-2 lands) `docs/plans/2026-05-16-osmotic-pressure-pr3.md` and the merged PR.
6. Updated `verification-report.md v0.2` for Bermuda.
7. New worked example workspace at `verifiers/osmotic_pressure/`.

## Open questions

1. **Z3 build feasibility on this machine.** `z3.rs 0.20` with `features = ["bundled"]` vendors Z3 and builds it via CMake + a C++ toolchain. Is that toolchain available? If `cargo check --no-default-features --features smt` fails for environmental reasons during PR-1, the fallback is to run the build in GitHub Actions and capture the verdict.edn there. Decision deferred until PR-1 dev work begins.

2. **Predicate map evolution — single source of truth?** Today predicates live in `rules/predicates.edn` (regex) AND in `rust-verifier/src/canonical.rs` (Z3 axiom). For v0.3 we keep both files but cross-link them via comments and add `verifiers/bermuda/docs/adding-a-predicate.md` as the procedural binding. Unifying both into a single declarative file is v0.4.

3. **Append-only ledger growth.** PR-2 adds 4 claims to the Bermuda ledger. Per `book-knowledge` convention, this is an append; new `claim_id`s are minted (`clm-2026-NNNNNN` continuing from the existing sequence). No state transitions on existing rows. We will not use book-knowledge's ingest pipeline (which is for source documents); we'll append directly with `status: verified` and a synthetic source-span pointing at `canonical-facts.md`. Whether this should go through book-knowledge proper is a v0.4 consideration.
