# Design: tier5-metta-backend

## Choice of MeTTa runtime

Three candidates were considered:

- **(a) `hyperon` Rust crate (hyperon-experimental).** The
  OpenCog Foundation's reference implementation. Native Rust,
  embeddable, exposes `hyperon::Metta`, `hyperon::space::*`,
  and the grounded-atom protocol that lets Rust functions
  participate in MeTTa evaluation. Crate is **alpha** per its
  own README — versions <1.0, API can break between minor
  releases.
- (b) MeTTa via Python `hyperon` PyPI wheel called over a
  subprocess. Adds a Python dependency to the verifier binary,
  adds IPC latency, and forks the alpha surface across two
  language bindings.
- (c) Hand-rolled equational-rewrite engine. Reinvents
  hyperon-experimental's pattern matcher, atomspace, and
  superpose/collapse semantics. The framework already imitates
  MeTTa idioms in EDN; doubling down on the imitation defeats
  the purpose of this tier.

**Decision: (a).** The integration cost is paid once and the
result is a real interpreter, not another scaffold. The alpha
caveat is real and must be documented in two places (proposal
and SUPPORT_MATRIX row).

## Version pin

`Cargo.toml` (optional, gated on the new `metta` feature):

```toml
hyperon = { version = "0.2", optional = true, default-features = false }
```

Because hyperon-experimental is alpha, the framework pins to a
known-working version *and* a known-working git rev in
`Cargo.lock`. Update procedure documented in
`docs/booklogic-dsl-reference.md` §2.5: bump the version in one
PR, run the integration tests, expect drift.

## `metta.rs` module shape

```rust
use hyperon::metta::runner::Metta;
use hyperon::space::grounding::GroundingSpace;

#[derive(Debug, thiserror::Error)]
pub enum MettaError {
    #[error("metta interpreter error: {0}")]
    Interpreter(String),
    #[error("metta evaluation timed out after {0} ms")]
    Timeout(u64),
}

pub fn run_metta(program: &str) -> Result<Vec<String>, MettaError> {
    let metta = Metta::new(None);  // fresh &self space
    // ... evaluate, collect printed atoms, return
}
```

The function returns the printed form of each `!`-evaluated atom
in the order they appear. Internal panics inside the interpreter
are caught via `std::panic::catch_unwind` and surfaced as
`MettaError::Interpreter`.

## EDN-to-MeTTa surface translation

Phase O ships only the constraint-shape translation; the
general EDN ↔ MeTTa bijection lives in change
`tier5-edn-metta-bijection`. For this change, `:assert` forms
follow a narrow shape:

```edn
(defconstraint C123-example
  :backend :metta
  :assert (= (lhs ?x) (rhs ?x))
  :on-unsat {:defect :example-violated})
```

translates to the MeTTa program:

```
(= (lhs $x) (rhs $x))
!(match &self (= (lhs $x) (rhs $x)) found)
```

`run_metta` returns `["found"]` on success; an empty result
fires the constraint's `:on-unsat` defect. The `_emit_metta_block`
emitter mirrors `_emit_egg_block` and `_emit_cozo_block` (lines
563 and 1055 of `codegen_axioms.py`).

## Verdict shape extension

```edn
{:status :unsat
 :z3-unsat-core [...]
 :cozo-defects {...}
 :metta-results
   {:C123-example {:state :unsat
                    :results []
                    :elapsed-ms 42}
    :C124-other   {:state :sat
                    :results ["found"]
                    :elapsed-ms 17}
    :C125-broken  {:state :error
                    :message "match: expected list, got nil"}}
 :warnings [{:phase :metta :reason :metta-timeout :constraint :C126 :elapsed-ms 30042}]}
```

The combined `:status` rolls up MeTTa's verdict the same way it
rolls up Cozo's: `:unsat` on any `:metta` defect of severity
`:fatal`.

## Error vs timeout vs unsat-defect

Three distinct paths:

- **Unsat defect** (REQ-METTA-041): the MeTTa query returned no
  results — the constraint is violated. The constraint's
  `:on-unsat` action fires, just like Z3's unsat path.
- **Interpreter error** (REQ-METTA-043): the program is
  malformed, the interpreter panics, or the alpha runtime
  surfaces a bug. The verdict carries `:metta-error` with the
  constraint id and the stringified error; the verifier process
  does NOT crash. Severity is `:warn`, not `:fatal` — an alpha
  runtime erroring is not a constraint violation.
- **Timeout** (REQ-METTA-044): a `:warnings` entry fires;
  the constraint is treated as `:not-discharged`, neither sat
  nor unsat. Severity is `:warn`.

## Thread isolation

Mirroring the Phase J solver-partitioning pattern, each
`metta::run_metta` invocation builds a fresh `Metta` instance
on the calling thread. No state crosses constraints; the
embedded interpreter is not Send+Sync-safe across all alpha
versions and we do not rely on shared state.

## SUPPORT_MATRIX update

One new row:

```
| `defconstraint :backend :metta` | wired (alpha) | `metta.rs::run_metta` | hyperon-experimental | wired (alpha) |
```

A new legend entry `wired (alpha)` explains the alpha qualifier:
"the underlying runtime crate publishes itself as alpha — API
and semantics may shift between minor versions; the framework
pins to a known-working rev." The existing three backends are
unchanged.

## Test surface

A new file
`verifiers/osmotic_pressure/rust-verifier/tests/metta_smoke.rs`
exercises a 3-atom program:

```
(= (parent Alice Bob) True)
(= (grandparent $x $z) (and (parent $x $y) (parent $y $z)))
!(match &self (= (parent Alice Bob) True) found)
```

The test asserts `run_metta` returns `["found"]`. A sibling
`metta_error.rs` fixture asserts the interpreter-error path; a
`metta_timeout.rs` fixture asserts the timeout path.

## Why this is purely additive

Z3 / egg / Cozo dispatch branches in `codegen_axioms.py` are
not modified; a new `elif backend == Keyword("metta")` branch
joins the existing `:z3` / `:egg` / `:cozo` matchers. The
verdict shape adds `:metta-results` but does not change the
meaning of any existing field. SUPPORT_MATRIX gains one row;
no row flips. The `:metta` Cargo feature is opt-in, so
verifier builds without `--features metta` are byte-identical
to today's binaries.
