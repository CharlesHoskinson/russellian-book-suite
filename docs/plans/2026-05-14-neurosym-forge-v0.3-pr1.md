# neurosym-forge v0.3 PR-1 — Hardening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land neurosym-forge v0.3 hardening so the scaffolded Rust addon can actually verify (not just return Sat unconditionally), the build does not require libpng/pkg-config, and `--out` accepts relative paths with `..` that resolve under cwd.

**Architecture:** Modify the project-template Rust files (`Cargo.toml.tmpl`, `lib.rs.tmpl`, `ir.rs.tmpl`, `smt.rs.tmpl`, new `axioms.rs.tmpl`) so a freshly-scaffolded project's Rust side parses EDN-as-JSON atoms via serde-json, calls a project-local `axioms::assert_axioms` hook, asserts each atom with `assert_and_track`, and returns a real `:sat`/`:unsat` verdict. Make tectonic an optional Cargo feature so default builds skip the libpng dependency. Relax `scaffold_project.py`'s `--out` policy to allow relative `..` paths that resolve under cwd. Spec at `docs/specs/2026-05-14-neurosym-forge-v0.3-mission-design.md` § "PR-1 detail".

**Tech Stack:** Python 3.13, jsonschema, jinja2, pytest (existing skill tooling). The Rust templates target z3.rs 0.20, serde_json 1, napi-rs 3. No actual Rust build runs in this PR — verification is via template-shape tests (string searches against `.tmpl` files).

---

## Pre-flight

Read these before starting:
- `docs/specs/2026-05-14-neurosym-forge-v0.3-mission-design.md` § "PR-1 detail"
- `skills/neurosym-forge/scripts/scaffold_project.py` (current `--out` policy at lines ~55-70, depending on local state)
- `skills/neurosym-forge/assets/project-template/rust-verifier/` (the current state of templates)
- `skills/neurosym-forge/tests/test_scaffold_project.py` (existing test patterns)
- `verifiers/bermuda/rust-verifier/src/canonical.rs` (the live `assert_bermuda_axioms` + `assert_tracked_atom` reference implementation — PR-2 will wire this in)

**Worktree:** This plan executes in `C:\Users\charl\code\russellian-book-suite-forge-v0.3` on branch `spec/forge-v0.3`. The spec is already committed.

**Test invocation:** `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q`. The venv was created during PR #14 and PR #18 work. If missing:

```bash
cd skills/neurosym-forge
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
```

**Commit hygiene:** Per repo CLAUDE.md — terse human style, no AI attribution, no Co-Authored-By, one problem per commit.

**No Rust build in this PR.** The neurosym-forge skill has no Rust toolchain dependency. PR-1's verification is via Python template-shape tests. PR-2 builds the actual cargo project against Bermuda.

---

## File Structure

### Created

```
skills/neurosym-forge/
├── assets/project-template/rust-verifier/src/
│   └── axioms.rs.tmpl                           NEW: no-op axioms hook
└── tests/
    └── test_rust_template_shape.py              NEW: template-shape tests
```

### Modified

```
skills/neurosym-forge/
├── assets/project-template/rust-verifier/
│   ├── Cargo.toml.tmpl                          tectonic optional + features section
│   └── src/
│       ├── lib.rs.tmpl                          mod axioms; gate render_pdf+typeset under pdf feature
│       ├── ir.rs.tmpl                           real serde-json parse_formulas
│       └── smt.rs.tmpl                          real Z3 walk + axioms hook + assert_and_track
├── scripts/scaffold_project.py                  --out .. relaxed
└── tests/test_scaffold_project.py               3 new tests
```

---

## Phase 1: `--out` policy relaxation

### Task 1.1: Tests for `--out` policy

**Files:**
- Modify: `skills/neurosym-forge/tests/test_scaffold_project.py`

- [ ] **Step 1: Add three failing tests at the end of the file.**

```python
def test_relative_dotdot_under_cwd_accepted(tmp_path: Path, skill_root: Path,
                                             monkeypatch) -> None:
    """`--out ../verifiers/x` from a sibling cwd resolves to a path under
    the original cwd; this is allowed."""
    # Make tmp_path the cwd so a relative .. resolves under it
    parent = tmp_path
    workdir = parent / "work"
    workdir.mkdir()
    target = parent / "verifiers" / "demo"
    monkeypatch.chdir(workdir)
    scaffold_project(
        project_name="Demo", project_slug="demo",
        out_dir=Path("..") / "verifiers" / "demo",
        skill_root=skill_root,
    )
    assert target.exists()


def test_absolute_outside_cwd_accepted(tmp_path: Path, skill_root: Path,
                                       monkeypatch) -> None:
    """An absolute path outside cwd is allowed (operator opt-in)."""
    inside = tmp_path / "inside"
    inside.mkdir()
    outside = tmp_path / "outside_abs" / "demo"
    monkeypatch.chdir(inside)
    scaffold_project(
        project_name="Demo", project_slug="demo",
        out_dir=outside.resolve(),
        skill_root=skill_root,
    )
    assert outside.exists()


def test_relative_dotdot_escaping_cwd_rejected(tmp_path: Path, skill_root: Path,
                                                monkeypatch) -> None:
    """A relative path with `..` that resolves OUTSIDE cwd is rejected."""
    inside = tmp_path / "deep" / "nested" / "cwd"
    inside.mkdir(parents=True)
    monkeypatch.chdir(inside)
    with pytest.raises(ValueError, match="outside the current working directory"):
        scaffold_project(
            project_name="Demo", project_slug="demo",
            out_dir=Path("..") / ".." / ".." / ".." / "escape",
            skill_root=skill_root,
        )
```

- [ ] **Step 2: Run, expect FAIL for two of three.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_scaffold_project.py::test_relative_dotdot_under_cwd_accepted tests/test_scaffold_project.py::test_absolute_outside_cwd_accepted tests/test_scaffold_project.py::test_relative_dotdot_escaping_cwd_rejected -v
```

Expected: `test_relative_dotdot_under_cwd_accepted` fails (current policy rejects any `..`); `test_absolute_outside_cwd_accepted` passes (current policy accepts absolute); `test_relative_dotdot_escaping_cwd_rejected` may pass with a different error message — that's OK at this stage.

- [ ] **Step 3: Find and replace the `--out` check in `scaffold_project.py`.**

In `skills/neurosym-forge/scripts/scaffold_project.py`, find the block that checks for `..`:

```python
out_str = str(out_dir)
if ".." in Path(out_str).parts:
    raise ValueError(f"--out must not contain '..' segments; got {out_str!r}")
out_dir = Path(out_str).resolve()
```

Replace with:

```python
out_str = str(out_dir)
resolved = Path(out_str).resolve()
cwd = Path.cwd().resolve()
if not Path(out_str).is_absolute() and not resolved.is_relative_to(cwd):
    raise ValueError(
        f"--out {out_str!r} resolves to {resolved}, which is outside the "
        f"current working directory {cwd}; pass an absolute path if intentional"
    )
out_dir = resolved
```

- [ ] **Step 4: Run, expect all three to PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_scaffold_project.py -v
```

Expected: all scaffold_project tests pass (existing + 3 new).

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/scaffold_project.py skills/neurosym-forge/tests/test_scaffold_project.py
git commit -m "neurosym-forge: relax --out policy for relative paths under cwd"
```

---

## Phase 2: Template-shape test framework

### Task 2.1: New test file `test_rust_template_shape.py`

Template-shape tests do string searches against the `.tmpl` files in `assets/project-template/`. They catch template drift without requiring Rust to build. They are TDD-style: write expectations against the **future** template state, fail, update templates, pass.

**Files:**
- Create: `skills/neurosym-forge/tests/test_rust_template_shape.py`

- [ ] **Step 1: Write the file with 5 tests for future template state.**

```python
"""Template-shape tests for the scaffolded Rust addon.

These tests verify the .tmpl files have the right structure to produce a
Rust crate that actually verifies (calls Z3, asserts axioms, tracks atoms
for unsat-core extraction). They do not build Rust; they only string-search
the template content.
"""
from __future__ import annotations

from pathlib import Path

import pytest


TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "assets" / "project-template"
RUST_SRC = TEMPLATE_ROOT / "rust-verifier" / "src"


def _read(name: str) -> str:
    p = RUST_SRC / name if not name.startswith("Cargo") else TEMPLATE_ROOT / "rust-verifier" / name
    return p.read_text(encoding="utf-8")


def test_axioms_template_exists() -> None:
    assert (RUST_SRC / "axioms.rs.tmpl").exists()


def test_axioms_template_is_no_op() -> None:
    """The default scaffold ships a no-op axioms hook; projects override it."""
    text = _read("axioms.rs.tmpl")
    assert "pub fn assert_axioms" in text
    # No-op body: either empty `{}`, a comment-only body, or `()` returned.
    # We assert it does NOT do anything dangerous like calling Z3 directly.
    assert "solver.assert" not in text


def test_smt_template_calls_axioms_hook() -> None:
    text = _read("smt.rs.tmpl")
    assert "crate::axioms::assert_axioms" in text or "axioms::assert_axioms" in text, \
        "smt.rs.tmpl must call axioms::assert_axioms"


def test_smt_template_uses_assert_and_track() -> None:
    text = _read("smt.rs.tmpl")
    assert "assert_and_track" in text, \
        "smt.rs.tmpl must use assert_and_track for unsat-core extraction"


def test_lib_template_pdf_is_feature_gated() -> None:
    """render_pdf and the typeset mod must be gated under `pdf` feature."""
    text = _read("lib.rs.tmpl")
    # render_pdf entry point gated
    pdf_gate_idx = text.find("#[cfg(feature = \"pdf\")]")
    render_pdf_idx = text.find("pub fn render_pdf")
    assert pdf_gate_idx != -1, "lib.rs.tmpl missing #[cfg(feature = \"pdf\")]"
    assert render_pdf_idx != -1
    assert pdf_gate_idx < render_pdf_idx, "feature gate must precede render_pdf"


def test_cargo_template_has_feature_flags() -> None:
    """Cargo.toml.tmpl must declare optional deps and a [features] section."""
    text = _read("Cargo.toml.tmpl")
    assert "[features]" in text
    assert "pdf" in text
    assert "default" in text
    # Optional deps
    assert "optional = true" in text


def test_cargo_template_tectonic_optional() -> None:
    text = _read("Cargo.toml.tmpl")
    # tectonic dep should be marked optional
    assert "tectonic" in text
    # Either explicitly `tectonic = { ... optional = true }` or in [features] dep:tectonic
    has_optional = (
        'tectonic = {' in text and 'optional = true' in text
    ) or 'dep:tectonic' in text
    assert has_optional, "tectonic must be optional in Cargo.toml.tmpl"


def test_ir_template_parses_atoms_array() -> None:
    """ir.rs.tmpl must parse the 'atoms' array from EDN-as-JSON, not return empty."""
    text = _read("ir.rs.tmpl")
    assert 'atoms' in text, "ir.rs.tmpl must reference the 'atoms' array"
    # The stub `Ok(Vec::new())` should be gone; serde_json should be used
    assert 'serde_json' in text or '"atoms"' in text
```

- [ ] **Step 2: Run, expect 8 fails (every test fails because templates are still v0.2).**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_rust_template_shape.py -v
```

Expected: all 8 tests fail (`axioms.rs.tmpl` doesn't exist; pdf gate not in lib.rs; no [features] section; etc.). These failures drive the template work in Phases 3-7.

- [ ] **Step 3: Commit the failing test file (TDD red phase).**

```bash
git add skills/neurosym-forge/tests/test_rust_template_shape.py
git commit -m "neurosym-forge: template-shape tests for v0.3 Rust contract (red)"
```

---

## Phase 3: Cargo.toml.tmpl feature flags

### Task 3.1: Make tectonic optional + add features section

**Files:**
- Modify: `skills/neurosym-forge/assets/project-template/rust-verifier/Cargo.toml.tmpl`

- [ ] **Step 1: Replace the file with the v0.3 content.**

```toml
[package]
name    = "{{ project_slug }}-verifier"
version = "0.1.0"
edition = "2024"

[lib]
crate-type = ["cdylib"]

[features]
default = ["smt", "eqsat", "kg"]
smt   = ["dep:z3"]
eqsat = ["dep:egg"]
kg    = ["dep:cozo"]
pdf   = ["dep:tectonic"]

[dependencies]
napi          = { version = "3", features = ["napi9", "serde-json", "async"] }
napi-derive   = "3"
serde         = { version = "1", features = ["derive"] }
serde_json    = "1"
thiserror     = "2"
ordered-float = "4"

z3            = { version = "0.20", features = ["bundled"], optional = true }
egg           = { version = "0.10", optional = true }
cozo          = { version = "0.7", default-features = false, features = ["compact"], optional = true }
tectonic      = { version = "0.16", optional = true }

[build-dependencies]
napi-build = "2"
```

Note `edn-rs` is dropped — Phase 5 switches `ir.rs.tmpl` to use `serde_json` instead, which the scaffold already needs for napi.

- [ ] **Step 2: Run the cargo template-shape tests, expect 2 PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_rust_template_shape.py::test_cargo_template_has_feature_flags tests/test_rust_template_shape.py::test_cargo_template_tectonic_optional -v
```

Expected: both pass.

- [ ] **Step 3: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/rust-verifier/Cargo.toml.tmpl
git commit -m "neurosym-forge: Cargo.toml features section, tectonic optional"
```

---

## Phase 4: New `axioms.rs.tmpl`

### Task 4.1: No-op axioms hook template

**Files:**
- Create: `skills/neurosym-forge/assets/project-template/rust-verifier/src/axioms.rs.tmpl`

- [ ] **Step 1: Write the template.**

```rust
//! Project-specific axioms. Override this file (or replace with a
//! domain-specific module like `canonical.rs`) to assert hard constraints
//! before the per-atom tracked assertions in `smt::check_all`.
//!
//! The default ships a no-op so a freshly-scaffolded project compiles
//! and verifies trivially (all-Sat) until the project author writes
//! its axioms.

#[cfg(feature = "smt")]
use z3::{Context, Solver};

#[cfg(feature = "smt")]
pub fn assert_axioms(_ctx: &Context, _solver: &Solver) {
    // No-op default. Domain-specific verifiers replace this body.
}

#[cfg(not(feature = "smt"))]
pub fn assert_axioms() {
    // No-op default for builds without the smt feature.
}
```

- [ ] **Step 2: Run the axioms shape tests, expect 2 PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_rust_template_shape.py::test_axioms_template_exists tests/test_rust_template_shape.py::test_axioms_template_is_no_op -v
```

Expected: both pass.

- [ ] **Step 3: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/rust-verifier/src/axioms.rs.tmpl
git commit -m "neurosym-forge: axioms.rs.tmpl no-op hook"
```

---

## Phase 5: Real `ir.rs.tmpl`

### Task 5.1: serde-json-based atom parser

**Files:**
- Modify: `skills/neurosym-forge/assets/project-template/rust-verifier/src/ir.rs.tmpl`

- [ ] **Step 1: Replace the file.**

```rust
//! Intermediate representation between Python ingest/extract and the SMT
//! solver. The Python helpers write EDN-as-JSON files with shape:
//!
//! {
//!   "version": 1,
//!   "atoms": [
//!     {"kind": "expression", "id": "clm-...", "predicate": ":x", "subject": ":Y", "value": 9, ...},
//!     {"kind": "symbol", "id": "...", "name": ":CONTEXT", "context": true, ...}
//!   ]
//! }
//!
//! `parse_formulas` returns one `(ClaimId, serde_json::Value)` per atom;
//! `smt::check_all` does typed dispatch.

use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    #[error("parse: {0}")]
    Parse(String),
    #[error("smt: {0}")]
    Smt(String),
    #[error("kg: {0}")]
    Kg(String),
}

pub type ClaimId = String;

/// An atom from the Python ingester / prose extractor.
///
/// Represented as a raw `serde_json::Value` so the SMT walk in `smt.rs`
/// can dispatch on `kind` and `predicate` without committing to a fixed
/// Rust enum (which would need updates every time the predicate map grows).
pub type Atom = serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Verdict {
    pub status: String,
    #[serde(default)]
    pub verified: Vec<Claim>,
    #[serde(default)]
    pub core: Vec<ClaimId>,
    #[serde(default)]
    pub explanation: String,
    #[serde(default)]
    pub graph_summary: Option<GraphSummary>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct GraphSummary {
    pub claim_count: usize,
    pub contradictions: Vec<(String, String)>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Claim {
    pub id: ClaimId,
    pub source: String,
}

/// Parse the EDN-as-JSON atomspace into a vector of (id, atom) pairs.
pub fn parse_formulas(edn: &str) -> Result<Vec<(ClaimId, Atom)>, Error> {
    let parsed: serde_json::Value = serde_json::from_str(edn)
        .map_err(|e| Error::Parse(e.to_string()))?;
    let atoms = parsed
        .get("atoms")
        .and_then(|v| v.as_array())
        .ok_or_else(|| Error::Parse("missing atoms array".into()))?;
    let mut out = Vec::with_capacity(atoms.len());
    for a in atoms {
        let id = a.get("id").and_then(|v| v.as_str()).unwrap_or("?").to_string();
        out.push((id, a.clone()));
    }
    Ok(out)
}

/// Serialize the verdict back to JSON for the CLJS bridge.
pub fn emit_verdict(v: &Verdict) -> String {
    serde_json::to_string(v).unwrap_or_else(|_| "{\"status\":\"unknown\"}".to_string())
}
```

Key changes from v0.2:
- `Formula` replaced by `pub type Atom = serde_json::Value` (typed dispatch deferred to smt.rs)
- `Error` enum extended with `Smt(...)` and `Kg(...)` variants so smt.rs and kg.rs can return them
- `parse_formulas` actually parses the `atoms` array instead of returning empty
- `Verdict` gains an `explanation` field consistent with the verdict.edn shape that `verdict_to_qa.py` expects

- [ ] **Step 2: Run the ir test, expect PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_rust_template_shape.py::test_ir_template_parses_atoms_array -v
```

Expected: pass.

- [ ] **Step 3: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/rust-verifier/src/ir.rs.tmpl
git commit -m "neurosym-forge: ir.rs.tmpl real serde-json atom parser"
```

---

## Phase 6: Real `smt.rs.tmpl`

### Task 6.1: Z3 walk with axioms hook + assert_and_track

**Files:**
- Modify: `skills/neurosym-forge/assets/project-template/rust-verifier/src/smt.rs.tmpl`

- [ ] **Step 1: Replace the file.**

```rust
//! SMT verification entry point.
//!
//! Walk the atoms parsed by `ir::parse_formulas`. For each atom that
//! carries a typed `predicate`+`subject`+`value`, assert the equality
//! to a Z3 variable named `{predicate}_{subject}` with `assert_and_track`
//! using the atom's `id`. Context/opaque atoms are skipped.
//!
//! Before the per-atom assertions, call `crate::axioms::assert_axioms`
//! which projects override to install hard constraints (the v0.3 hook
//! contract).
//!
//! `solver.check()` returns Sat / Unsat / Unknown. On Unsat we read
//! the unsat core (a vector of tracker booleans) and translate the
//! tracker names back to ClaimIds.

use crate::ir::{Atom, ClaimId, Error, Verdict};

#[cfg(feature = "smt")]
use z3::{
    ast::{Ast, Bool, Int, Real, String as Z3String},
    Config, Context, SatResult, Solver,
};

#[cfg(feature = "smt")]
pub fn check_all(formulas: &[(ClaimId, Atom)]) -> Result<Verdict, Error> {
    let cfg = Config::new();
    let ctx = Context::new(&cfg);
    let solver = Solver::new(&ctx);

    // Project-specific axioms (default no-op).
    crate::axioms::assert_axioms(&ctx, &solver);

    let mut tracker_ids: Vec<ClaimId> = Vec::with_capacity(formulas.len());

    for (id, atom) in formulas {
        // Skip context / opaque / non-expression atoms.
        let kind = atom.get("kind").and_then(|v| v.as_str()).unwrap_or("");
        if kind != "expression" {
            continue;
        }
        let predicate = match atom.get("predicate").and_then(|v| v.as_str()) {
            Some(p) => p.trim_start_matches(':'),
            None => continue,
        };
        let subject = match atom.get("subject").and_then(|v| v.as_str()) {
            Some(s) => s.trim_start_matches(':'),
            None => continue,
        };
        let var_name = format!("{}_{}", predicate, subject);
        let tracker = Bool::new_const(&ctx, id.as_str());

        let Some(value) = atom.get("value") else {
            continue;
        };

        let assertion: Bool = match value {
            serde_json::Value::Number(n) if n.is_i64() => {
                let v = n.as_i64().unwrap();
                let z3_var = Int::new_const(&ctx, var_name.as_str());
                z3_var._eq(&Int::from_i64(&ctx, v))
            }
            serde_json::Value::Number(n) if n.is_f64() => {
                let v = n.as_f64().unwrap();
                // Represent as rational with 1e-6 tolerance via Real.
                let z3_var = Real::new_const(&ctx, var_name.as_str());
                let numerator = (v * 1_000_000.0) as i32;
                z3_var._eq(&Real::from_real(&ctx, numerator, 1_000_000))
            }
            serde_json::Value::String(s) => {
                let z3_var = Z3String::new_const(&ctx, var_name.as_str());
                let lit = Z3String::from_str(&ctx, s)
                    .map_err(|_| Error::Smt(format!("invalid string literal: {s:?}")))?;
                z3_var._eq(&lit)
            }
            serde_json::Value::Bool(b) => {
                let z3_var = Bool::new_const(&ctx, var_name.as_str());
                z3_var._eq(&Bool::from_bool(&ctx, *b))
            }
            _ => continue,
        };
        solver.assert_and_track(&assertion, &tracker);
        tracker_ids.push(id.clone());
    }

    match solver.check() {
        SatResult::Sat => Ok(Verdict {
            status: "sat".into(),
            core: Vec::new(),
            ..Default::default()
        }),
        SatResult::Unsat => {
            let core_bools = solver.get_unsat_core();
            let core_ids: Vec<ClaimId> = core_bools
                .iter()
                .map(|b| format!("{b}"))
                .map(|s| s.trim_matches('|').to_string())
                .filter(|s| tracker_ids.iter().any(|tid| tid == s))
                .collect();
            Ok(Verdict {
                status: "unsat".into(),
                core: core_ids,
                explanation: "Z3 reports unsat; offending atoms in core".into(),
                ..Default::default()
            })
        }
        SatResult::Unknown => Ok(Verdict {
            status: "unknown".into(),
            explanation: solver.get_reason_unknown().unwrap_or_default(),
            ..Default::default()
        }),
    }
}

#[cfg(not(feature = "smt"))]
pub fn check_all(_formulas: &[(ClaimId, Atom)]) -> Result<Verdict, Error> {
    Err(Error::Smt("compiled without `smt` feature".into()))
}
```

Key changes from v0.2:
- Calls `crate::axioms::assert_axioms` before per-atom assertions
- Per-atom assertions use `assert_and_track` with the atom's id
- Returns real `:sat`/`:unsat`/`:unknown` based on `solver.check()`
- On `:unsat`, extracts the unsat core and maps trackers back to claim IDs
- Float values handled via rational approximation (Real with 1e-6 granularity)
- Feature-gated: builds without `smt` return an error from `check_all`

- [ ] **Step 2: Run smt shape tests, expect 2 PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_rust_template_shape.py::test_smt_template_calls_axioms_hook tests/test_rust_template_shape.py::test_smt_template_uses_assert_and_track -v
```

Expected: both pass.

- [ ] **Step 3: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/rust-verifier/src/smt.rs.tmpl
git commit -m "neurosym-forge: smt.rs.tmpl real Z3 walk with axioms hook"
```

---

## Phase 7: `lib.rs.tmpl` updates

### Task 7.1: Add mod axioms; gate render_pdf+typeset under pdf feature

**Files:**
- Modify: `skills/neurosym-forge/assets/project-template/rust-verifier/src/lib.rs.tmpl`

- [ ] **Step 1: Replace the file.**

```rust
#![deny(clippy::all)]
use napi_derive::napi;

mod ir;
mod axioms;
mod smt;

#[cfg(feature = "eqsat")]
mod eqsat;

#[cfg(feature = "kg")]
mod kg;

#[cfg(feature = "pdf")]
mod typeset;

#[napi]
pub fn verify_formulas(formulas_edn: String) -> napi::Result<String> {
    let formulas = ir::parse_formulas(&formulas_edn)
        .map_err(|e| napi::Error::from_reason(format!("parse: {e}")))?;
    let verdict = smt::check_all(&formulas)
        .map_err(|e| napi::Error::from_reason(format!("smt: {e}")))?;
    #[cfg(feature = "kg")]
    let verdict = {
        let mut v = verdict;
        let kg_summary = kg::ingest_and_summarize(&v.verified)
            .map_err(|e| napi::Error::from_reason(format!("kg: {e}")))?;
        v.graph_summary = Some(kg_summary);
        v
    };
    Ok(ir::emit_verdict(&verdict))
}

#[cfg(feature = "eqsat")]
#[napi]
pub fn saturate(terms_edn: String, rules_edn: String) -> napi::Result<String> {
    eqsat::saturate(&terms_edn, &rules_edn)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[cfg(feature = "pdf")]
#[napi]
pub fn render_pdf(latex: String, out_path: String) -> napi::Result<()> {
    typeset::render(&latex, &out_path)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}
```

Key changes from v0.2:
- `mod axioms;` added (always — axioms is feature-internal-gated for `smt`)
- `mod eqsat;`, `mod kg;`, `mod typeset;` gated under their feature flags
- `verify_formulas` keeps kg integration but it is now feature-gated (`#[cfg(feature = "kg")]` block extends the verdict only when the feature is enabled)
- `saturate` and `render_pdf` gated under `eqsat` and `pdf` respectively

- [ ] **Step 2: Run lib shape test, expect PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_rust_template_shape.py::test_lib_template_pdf_is_feature_gated -v
```

Expected: pass.

- [ ] **Step 3: Run the full template-shape suite, expect all 8 PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_rust_template_shape.py -v
```

Expected: 8 passed.

- [ ] **Step 4: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/rust-verifier/src/lib.rs.tmpl
git commit -m "neurosym-forge: lib.rs.tmpl mod axioms + feature gating for pdf/eqsat/kg"
```

---

## Phase 8: Scaffold-shape integration test

### Task 8.1: Confirm a freshly-scaffolded project has the right shape

This integration test scaffolds a project to `tmp_path` and asserts the emitted Rust files match the new contract (axioms.rs present, lib.rs has `mod axioms`, Cargo.toml has `[features]`).

**Files:**
- Modify: `skills/neurosym-forge/tests/test_scaffold_project.py`

- [ ] **Step 1: Append three tests.**

```python
def test_scaffolded_axioms_rs_exists(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    axioms = tmp_project_root / "rust-verifier" / "src" / "axioms.rs"
    assert axioms.exists()
    text = axioms.read_text(encoding="utf-8")
    assert "pub fn assert_axioms" in text


def test_scaffolded_lib_rs_includes_mod_axioms(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    lib = (tmp_project_root / "rust-verifier" / "src" / "lib.rs").read_text(encoding="utf-8")
    assert "mod axioms;" in lib


def test_scaffolded_cargo_toml_has_features(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    cargo = (tmp_project_root / "rust-verifier" / "Cargo.toml").read_text(encoding="utf-8")
    assert "[features]" in cargo
    assert "pdf" in cargo
```

- [ ] **Step 2: Run, expect PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_scaffold_project.py -v
```

Expected: all pass (existing + 3 from Phase 1 + 3 new = ~12 scaffold tests total).

- [ ] **Step 3: Run the FULL suite to confirm no regressions.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: previous 73 + 3 (--out) + 8 (template shape) + 3 (scaffold integration) = ~87 passing. The exact final count depends on whether the existing test_scaffold_project count was 5 (as in the original plan) or higher after iteration. Verify the count is monotonically increasing from the v0.2 baseline; report the actual number.

- [ ] **Step 4: Commit.**

```bash
git add skills/neurosym-forge/tests/test_scaffold_project.py
git commit -m "neurosym-forge: scaffold integration tests for v0.3 Rust shape"
```

---

## Phase 9: SKILL.md + smoke + PR

### Task 9.1: Update SKILL.md

**Files:**
- Modify: `skills/neurosym-forge/SKILL.md`

- [ ] **Step 1: Read the current SKILL.md and find the "Composes with" + "See also" or feature-list sections.**

- [ ] **Step 2: Add a "What v0.3 added" line near the top of the body (after the one-line description).**

Append a sentence to the body's intro paragraph:

> v0.3 adds an `axioms.rs` hook contract so scaffolded projects can install Z3 hard constraints before per-atom verification, makes the `tectonic` dep optional (build with `--features pdf` to include PDF rendering), and accepts relative `--out` paths with `..` segments that resolve under the current working directory.

If the SKILL.md is body-length-conscious (the existing one is ~70 lines per Anthropic compliance), keep this one sentence. Do not add a full changelog.

- [ ] **Step 3: Run Anthropic compliance tests.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_anthropic_compliance.py -v
```

Expected: 6 passed (no body length regression).

- [ ] **Step 4: Commit.**

```bash
git add skills/neurosym-forge/SKILL.md
git commit -m "neurosym-forge: SKILL.md note v0.3 additions"
```

### Task 9.2: Update worked-example references

**Files:**
- Modify: `skills/neurosym-forge/references/grounded-atoms.md`

- [ ] **Step 1: Append a section on the v0.3 `axioms.rs` hook.**

Add a section at the end of `grounded-atoms.md`:

```markdown
## The axioms hook (v0.3+)

The scaffolded `rust-verifier/src/axioms.rs` ships a no-op `assert_axioms(ctx, solver)`
that the SMT walk in `smt.rs` calls before any per-atom tracked assertions. Projects
install hard constraints by replacing the body. Example: a chemistry domain might
assert `R = 8.314` as a Z3 constant; a book domain (like Bermuda) asserts each
canonical fact from `canonical-facts.md`.

Reference implementation: `verifiers/bermuda/rust-verifier/src/canonical.rs` ships
`assert_bermuda_axioms` and the `assert_tracked_atom` helper. The Bermuda project's
`axioms.rs` is a thin re-export shim so `crate::axioms::assert_axioms` resolves to
the bermuda-specific implementation.
```

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/references/grounded-atoms.md
git commit -m "neurosym-forge: document axioms.rs hook in grounded-atoms reference"
```

### Task 9.3: Smoke — scaffold a project end-to-end

**Files:** None (manual verification).

- [ ] **Step 1: Scaffold to a temp location.**

```bash
cd skills/neurosym-forge
.venv/Scripts/python.exe -m scripts.scaffold_project \
  --name "Smoke v0.3" --slug smoke_v03 \
  --out /tmp/smoke_v03
```

Expected output: `scaffolded smoke_v03 at /tmp/smoke_v03`.

- [ ] **Step 2: Verify the emitted files match the v0.3 contract.**

```bash
ls /tmp/smoke_v03/rust-verifier/src/
# Expect: axioms.rs, eqsat.rs, ir.rs, kg.rs, lib.rs, smt.rs, typeset.rs

grep -c "mod axioms" /tmp/smoke_v03/rust-verifier/src/lib.rs
# Expect: 1

grep -c "\[features\]" /tmp/smoke_v03/rust-verifier/Cargo.toml
# Expect: 1

grep -c "assert_and_track" /tmp/smoke_v03/rust-verifier/src/smt.rs
# Expect: at least 1
```

- [ ] **Step 3: Confirm lint_atomspace still works on the scaffolded seed.**

```bash
.venv/Scripts/python.exe -m scripts.lint_atomspace /tmp/smoke_v03/rules/seed.edn
```

Expected: `OK: atomspace ... passes (0 atoms, 0 rules)`.

- [ ] **Step 4: Cleanup.**

```bash
rm -rf /tmp/smoke_v03
```

No commit; this is a manual smoke step.

### Task 9.4: Push + open PR

- [ ] **Step 1: Push.**

```bash
cd C:/Users/charl/code/russellian-book-suite-forge-v0.3
git push -u origin spec/forge-v0.3
```

- [ ] **Step 2: Open the PR.**

```bash
gh pr create --title "neurosym-forge v0.3: hardening for the real verify path" --body "$(cat <<'EOF'
## Summary

Lands the v0.3 skill hardening so scaffolded projects ship a working Rust verifier instead of stubs.

- **axioms.rs hook**: new `rust-verifier/src/axioms.rs` template with a no-op `assert_axioms(ctx, solver)`; `smt.rs` calls it before per-atom assertions. Projects override the body to install Z3 hard constraints (canonical facts, domain laws, etc.).
- **Real Z3 walk**: `smt.rs` actually parses atoms, dispatches on `predicate`/`subject`/`value`, asserts each with `assert_and_track`, and returns `:sat`/`:unsat`/`:unknown` with the unsat core mapped back to claim IDs.
- **Real atom parser**: `ir.rs::parse_formulas` reads the EDN-as-JSON shape the Python ingester emits (not the old empty stub).
- **Tectonic optional**: `Cargo.toml.tmpl` declares `[features]` with `default = ["smt", "eqsat", "kg"]` and `pdf = ["dep:tectonic"]`. Default builds skip the libpng/pkg-config requirement.
- **`--out` policy relaxed**: relative paths with `..` that resolve under cwd are accepted; absolute paths anywhere are accepted; relative paths that escape cwd are rejected.

Spec: `docs/specs/2026-05-14-neurosym-forge-v0.3-mission-design.md` § PR-1 detail.
Plan: `docs/plans/2026-05-14-neurosym-forge-v0.3-pr1.md`.

## Test plan

- [ ] `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q` — expect ~87 tests passing (73 baseline + 14 new across `--out`, template shape, and scaffold integration)
- [ ] Manual scaffold smoke: `python -m scripts.scaffold_project --name X --slug x --out /tmp/x` produces a Rust tree with `axioms.rs`, `[features]` in Cargo.toml, and `mod axioms` in `lib.rs`
- [ ] No actual `cargo build` runs in this PR — that gets exercised in PR-2 against Bermuda

## Out of scope

- Wiring `verifiers/bermuda/canonical.rs` into the new `axioms` hook — PR-2
- Running `cargo build` and the real Z3 verifier — PR-2
- Second workspace (osmotic-pressure) — PR-3
EOF
)"
```

- [ ] **Step 3: Return the PR URL.**

---

## Self-review

Walking the spec § PR-1 detail against this plan:

| Spec clause | Implementing task |
|---|---|
| Tectonic feature flag in `Cargo.toml.tmpl` | Task 3.1 |
| `[features]` section with default, smt, eqsat, kg, pdf | Task 3.1 |
| Optional deps marked `optional = true` | Task 3.1 |
| Real `ir.rs.tmpl` with serde_json parse_formulas | Task 5.1 |
| Real `smt.rs.tmpl` with Context/Solver, axioms hook, assert_and_track, unsat core mapping | Task 6.1 |
| New `axioms.rs.tmpl` no-op default | Task 4.1 |
| `lib.rs.tmpl` mod axioms; gate render_pdf/typeset under pdf | Task 7.1 |
| `--out` policy relaxation | Task 1.1 |
| `test_relative_dotdot_under_cwd_accepted` | Task 1.1 |
| `test_absolute_outside_cwd_accepted` | Task 1.1 |
| `test_relative_dotdot_escaping_cwd_rejected` | Task 1.1 |
| `test_smt_template_calls_axioms_hook` | Task 2.1 |
| `test_smt_template_uses_assert_and_track` | Task 2.1 |
| `test_axioms_template_is_no_op` | Task 2.1 |
| `test_lib_template_pdf_is_feature_gated` | Task 2.1 |
| `test_cargo_template_has_feature_flags` | Task 2.1 |
| SKILL.md update for v0.3 features | Task 9.1 |
| Documentation pass | Task 9.2 (axioms hook in grounded-atoms.md) |

All spec PR-1 requirements have an implementing task.

**Placeholder scan:** No "TBD/TODO/fill in details" in plan steps. Every code step has the actual code. Every test step has the actual assertion or grep target.

**Type consistency:**
- `axioms::assert_axioms(&Context, &Solver)` used identically in axioms.rs.tmpl (Task 4.1) and smt.rs.tmpl (Task 6.1).
- `parse_formulas(&str) -> Result<Vec<(ClaimId, Atom)>, Error>` defined in Task 5.1, called the same way in Task 6.1 via `crate::ir::parse_formulas`.
- `Atom = serde_json::Value` is the contract; both ir.rs and smt.rs respect it.
- `Verdict::core: Vec<ClaimId>` consistent across ir.rs (Task 5.1) and smt.rs (Task 6.1).
- The feature names `smt`, `eqsat`, `kg`, `pdf` are used consistently across Cargo.toml.tmpl (Task 3.1), lib.rs.tmpl (Task 7.1), and the feature-gated `#[cfg(...)]` blocks in axioms.rs.tmpl (Task 4.1) and smt.rs.tmpl (Task 6.1).

No drift.

**Effort:** 1.5-2 days per spec. The plan has 9 phases; most are template edits (mechanical) plus one Python policy change (TDD).
