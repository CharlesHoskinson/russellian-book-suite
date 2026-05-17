# Capability delta: verifier-build — change: booklogic-pr4-active-forms

## ADD

### REQ-VERIFIER-BUILD-010 — Ubiquitous

The codegen output `rust-verifier/src/axioms.rs` shall be byte-deterministic
given the same `constraints.edn` source: two consecutive `python -m
scripts.codegen_axioms` invocations against the same input must produce
identical bytes.

**Rationale:** Lockstep checking depends on stable codegen.
**Tested by:** `test_codegen_axioms.py::test_codegen_is_deterministic` (added in pr4 T2.4)

### REQ-VERIFIER-BUILD-011 — Ubiquitous

After codegen, `cargo check --manifest-path <project>/rust-verifier/Cargo.toml
--features smt` shall complete with exit 0 against the BookLogic-generated
`axioms.rs` produced by the project template's sample constraints.

**Rationale:** Codegen must produce syntactically and type-valid Rust.
**Tested by:** `skills/neurosym-forge/tests/test_template_cargo_check.py::test_axioms_cargo_check` (added in pr4 T2.7)

### REQ-VERIFIER-BUILD-020 — Ubiquitous

The Rust verifier shall declare `cozo = "0.7"` with `default-features =
false` and `features = ["compact"]` as a non-optional dependency in
`rust-verifier/Cargo.toml.tmpl` (and the Bermuda lockstep `Cargo.toml`).

**Rationale:** Cozo backs the active `kg.rs` query path.
**Tested by:** `skills/neurosym-forge/tests/test_rust_template_shape.py::test_cozo_active_dep` (added in pr4 T3.3)

### REQ-VERIFIER-BUILD-021 — Ubiquitous

`cargo check --manifest-path <project>/rust-verifier/Cargo.toml --features kg`
shall complete with exit 0 against the BookLogic-generated `kg.rs` produced
by the project template's sample queries.

**Rationale:** Same gate as REQ-VERIFIER-BUILD-011, applied to the Cozo
data path.
**Tested by:** `test_template_cargo_check.py::test_kg_cargo_check` (added in pr4 T3.5)

### REQ-VERIFIER-BUILD-022 — Ubiquitous

The `.github/workflows/ci.yml` workflow shall include a job named
`booklogic-template-cargo-check` that runs `cargo check --features smt,kg`
against a scaffolded fresh project on every PR.

**Rationale:** Template-level cargo gate; PR-5 layers the Bermuda-specific
gate on top.
**Tested by:** Workflow run (added in pr4 T3.5)

## MODIFY

(none)

## REMOVE

(none)
