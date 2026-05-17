# Capability delta: verifier-build — change: booklogic-pr5-bermuda-migration

## ADD

### REQ-VERIFIER-BUILD-030 — Ubiquitous

`verifiers/bermuda/rust-verifier/src/axioms.rs` shall be regeneratable by
invoking the BookLogic compiler against `verifiers/bermuda/rules/`,
producing byte-identical output to the committed file.

**Rationale:** Lockstep check — manual edits to the generated file are
forbidden.
**Tested by:** `verifiers/bermuda/tests/test_axioms_lockstep.py::test_regen_matches_committed` (added in pr5 T2.2)

### REQ-VERIFIER-BUILD-031 — Ubiquitous

`verifiers/bermuda/tests/test_axioms_lockstep.py` shall execute on every
PR and fail loudly if the regenerated `axioms.rs` byte-differs from the
committed file.

**Rationale:** Drift detection.
**Tested by:** `verifiers/bermuda/tests/test_axioms_lockstep.py::test_regen_matches_committed` plus the `.github/workflows/ci.yml` `bermuda-z3-build` job that invokes it (added in pr5 T2.2)

### REQ-VERIFIER-BUILD-040 — Ubiquitous

The `.github/workflows/ci.yml` workflow shall include a job named
`bermuda-z3-build` on `ubuntu-latest` that runs `cargo build
--manifest-path verifiers/bermuda/rust-verifier/Cargo.toml --features z3`
on every PR and fails the PR if the build fails.

**Rationale:** Bundled Z3 build is the canonical CI gate; mission OQ #5.
**Tested by:** Workflow run on the PR (added in pr5 T5.1)

### REQ-VERIFIER-BUILD-041 — Ubiquitous

The `.github/workflows/ci.yml` workflow shall include a job
`bermuda-z3-verify` that, after `bermuda-z3-build` succeeds, runs the
real verifier against `examples/bermuda-manual/` and asserts the verdict
shape is well-formed.

**Rationale:** Build success isn't enough; the verifier must run.
**Tested by:** Workflow run (added in pr5 T5.2)

### REQ-VERIFIER-BUILD-042 — State-driven

While CI is the canonical verifier gate, `verifiers/bermuda/tests/test_run_verification.py`
shall not default to `stub_verifier=True`; tests defaulting to the real
verifier are the new norm. Tests explicitly setting `stub_verifier=True`
remain valid for fast local iteration.

**Rationale:** Stub-by-default masks real verifier regressions.
**Tested by:** `test_run_verification.py::test_default_uses_real_verifier` (added in pr5 T7.1)

## MODIFY

(none)

## REMOVE

(none)
