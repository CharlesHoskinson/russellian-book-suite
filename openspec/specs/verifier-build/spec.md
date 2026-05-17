# Capability: verifier-build

The Rust verifier build pipeline: cargo manifest, `edn-rs` / `z3` / `cozo`
/ `egg` dependencies, the napi-rs node addon, and the CI workflows that
gate real Z3 builds on `ubuntu-latest`. Covers `verifiers/bermuda/rust-verifier/`
and the analogous tree in scaffolded projects under
`skills/neurosym-forge/assets/project-template/`.

Sprints booklogic-pr4-active-forms (`cargo check` codegen gate) and
booklogic-pr5-bermuda-migration (`cargo build` + Z3 link CI gate) add
REQs.

## Requirements

_(none yet)_
