# Capability delta: metta-runtime — change: tier5-metta-backend

This change introduces a new capability `metta-runtime`, the
framework's hyperon-experimental-backed evaluation surface.
Today no `defconstraint :backend :metta` row exists in
`SUPPORT_MATRIX.md`; the framework imitates MeTTa idioms in EDN
but never links the real interpreter. After this change a
fourth live backend joins `:z3` / `:egg` / `:cozo`, flagged
`wired (alpha)` because hyperon-experimental publishes itself
as alpha.

## ADD

### REQ-METTA-040 — Ubiquitous

The framework SHALL ship a `verifiers/*/rust-verifier/src/metta.rs`
module that embeds the `hyperon = "0.2"` crate (the
hyperon-experimental Rust crate; alpha per its own README) and
exposes:

- `pub fn run_metta(program: &str) -> Result<Vec<String>, MettaError>`
  returning each `!`-evaluated atom's printed form, in
  evaluation order.
- `pub enum MettaError { Interpreter(String), Timeout(u64) }`
  capturing the two non-defect failure shapes.

The module SHALL compile under a new `metta` Cargo feature.
The `Cargo.toml` entry SHALL pin both the version and the
resolved git rev in `Cargo.lock` so alpha-runtime drift is
caught by review rather than by green-to-red CI surprise.

**Rationale:** Without an embedded interpreter, the framework
cannot honestly claim `:metta` as a backend. This REQ adds the
link.
**Tested by:** `verifiers/osmotic_pressure/rust-verifier/tests/metta_smoke.rs::three_atom_program_returns_expected_result` (added in O1.3)

### REQ-METTA-041 — Optional feature

WHERE a `defconstraint` form declares `:backend :metta`, the
framework SHALL translate the constraint's `:assert` form into
a MeTTa program string that:

- asserts the constraint into a fresh `&self` space via a `=`
  rewrite head, and
- evaluates a `!(match &self ...)` query against that space.

The framework SHALL fire the constraint's `:on-unsat` defect
when the match returns no results. The combined verdict's
`:status` SHALL roll up MeTTa's defect surface the same way it
rolls up Cozo's (worst-case of all backends' statuses).

**Rationale:** Gives `:metta` the same dispatch shape that
Tier 3 gave `:egg` and `:cozo`; an empty match is the MeTTa
analogue of Z3's `:unsat`.
**Tested by:** `tests/metta_backend.rs::metta_backed_constraint_affects_status` (added in O2.2)

### REQ-METTA-042 — Ubiquitous

The codegen SHALL emit a sibling
`pub fn metta_constraints() -> Vec<(String, String)>` registry
in the generated `axioms.rs` module, parallel to the
`cozo_constraints()` registry introduced in Phase I. The first
tuple element SHALL be the constraint id; the second SHALL be
the MeTTa program string. `lib.rs` SHALL feed each entry through
`metta::run_metta` and assemble the per-constraint verdict
fragment.

**Rationale:** Mirrors the established registry pattern from
the Cozo backend so the orchestration code in `lib.rs` is
uniform across backends.
**Tested by:** `tests/metta_registry.rs::metta_constraints_registry_lists_every_metta_backed_id` (added in O2.3)

### REQ-METTA-043 — Unwanted behaviour

IF the embedded MeTTa interpreter panics, returns a runtime
error, or yields a malformed atom during `make ci`, THEN the
verdict SHALL surface a `:metta-results <cid> {:state :error
:message <stringified-error>}` entry, and the verifier process
SHALL NOT crash. The catch SHALL wrap both `Metta::new` and
the evaluation call in `std::panic::catch_unwind`. Severity of
the entry SHALL be `:warn`, not `:fatal` — an alpha-runtime
bug is not a constraint violation, and SHALL NOT drive the
combined `:status` to `:unsat`.

**Rationale:** Alpha runtimes can panic on inputs the test
fixtures did not anticipate. A panic must surface as a
warning, not as a process exit.
**Tested by:** `tests/metta_error.rs::malformed_program_surfaces_metta_error_without_panic` (added in O3.3)

### REQ-METTA-044 — Optional feature

WHERE the env var `VERIFIER_METTA_TIMEOUT_MS` is set (default
30000), the framework SHALL bound each `run_metta` call by that
timeout via `thread::spawn` + `mpsc::recv_timeout`. On timeout
the framework SHALL surface a structured warning of the shape
`{:phase :metta :reason :metta-timeout :constraint :C###
:elapsed-ms <int>}` on the verdict's `:warnings` list and SHALL
continue evaluating the remaining constraints. The timed-out
constraint SHALL be reported as `:not-discharged`, NOT `:sat`
and NOT `:unsat`.

**Rationale:** MeTTa programs can fail to terminate (the
language is multivalued and Turing-complete); a per-program
timeout prevents one bad constraint from stalling the run.
**Tested by:** `tests/metta_timeout.rs::pathological_program_emits_timeout_warning_and_does_not_block` (added in O3.3)

### REQ-METTA-045 — Ubiquitous

`skills/neurosym-forge/SUPPORT_MATRIX.md` SHALL be updated as
part of this change so that:

- a new row `defconstraint :backend :metta` is added with
  Status `wired (alpha)`,
- a new legend entry `wired (alpha)` explains the qualifier:
  "the underlying runtime crate (hyperon-experimental)
  publishes itself as alpha; API and semantics may shift
  between minor versions; the framework pins to a
  known-working rev."

The drift-lint `tests/test_support_matrix.py` SHALL pass against
the updated matrix once `metta.rs` and the
`_emit_metta_block` codegen path land. The drift lint SHALL
assert the `(alpha)` qualifier is present on the row — losing
it accidentally is a regression.

**Rationale:** The alpha qualifier is load-bearing. Without it,
authors will read the matrix and assume the same stability
guarantees as `:z3` / `:egg` / `:cozo`; with it, the contract is
explicit.
**Tested by:** `tests/test_support_matrix.py::test_matrix_carries_metta_alpha_row` (added in O4.2)

### REQ-METTA-046 — Ubiquitous

The Z3, egg, and Cozo dispatch branches in
`codegen_axioms.py` SHALL remain unchanged. Adding the `:metta`
branch SHALL be purely additive: no existing `_emit_z3_block`,
`_emit_egg_block`, or `_emit_cozo_block` call site is touched,
no existing generated test changes byte-shape, and a verifier
build without `--features metta` SHALL produce binaries
byte-identical to today's binaries.

**Rationale:** Tier 5 must not regress Tiers 1-4. Additive-only
is the strongest guarantee available.
**Tested by:** `tests/test_codegen_axioms.py::test_existing_backends_unchanged_after_metta_addition` and a CI byte-equality check on the verifier binary without `--features metta` (added in O5.1)

### REQ-METTA-047 — Ubiquitous

A cargo integration test
`verifiers/osmotic_pressure/rust-verifier/tests/metta_smoke.rs`
SHALL exercise a 3-atom MeTTa program (a fact, a rule, and a
`!`-evaluated query) against the embedded runtime, and SHALL
assert the printed result equals the expected output. A sibling
test SHALL exist in `verifiers/bermuda/rust-verifier/tests/`
exercising the same fixture so the bermuda mirror is covered on
the same guarantee.

**Rationale:** Integration coverage is mandatory for a backend
moving from absent to wired. A 3-atom program is the smallest
fixture that exercises the fact + rule + query loop, which is
the minimum MeTTa surface the codegen needs.
**Tested by:** `verifiers/osmotic_pressure/rust-verifier/tests/metta_smoke.rs::three_atom_program_returns_expected_result` and the bermuda mirror (added in O1.3 and O5.2)
