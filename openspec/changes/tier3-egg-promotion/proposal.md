# Change: tier3-egg-promotion

**Tier:** 3 of 4 (promote a documented-but-stub backend to live)
**Branch:** `feat/tier3-egg-promotion`
**Depends on:** Tier 1 (binding-schema, canonical-var-name)

## Why

`SUPPORT_MATRIX.md` currently flags `defrule` as **stub** and
`defconstraint :backend :egg` as **DROP**. Authors writing rewrite
rules today get a CLJS-side string-substitution pass and nothing
else: the rule is recognised by the expander, registered in the
intermediate EDN, then silently dropped by
`codegen_axioms.py:139` (`if backend != Keyword("z3"): continue`).
A `(defconstraint ... :backend :egg ...)` form passes validation,
emits zero Z3 assertions, and produces a `:sat` verdict for the
wrong reason.

This is the most visible "promised but not delivered" path in the
framework. The `egg` crate is already a declared optional
dependency (`egg = "0.10"` in both verifier Cargo.toml files,
gated on the `eqsat` feature), but `eqsat.rs` is a one-line stub.
Until egg is live, the SUPPORT_MATRIX row reads as a confession.

## What

- Live `egg::Runner` integration in
  `verifiers/*/rust-verifier/src/eqsat.rs` that builds an EGraph
  from the BookLogic `defrule` set.
- During codegen, equality saturation runs over every
  `defconstraint` LHS/RHS pair and the canonical form is stored.
- Z3 axioms are emitted on the canonical form (post-saturation),
  never the surface form.
- `defconstraint :backend :egg` routes to egg's `prove` API
  instead of being dropped.
- Saturation budget (node-count limit, configurable via
  `VERIFIER_EQSAT_NODE_LIMIT`, default 10000) with a structured
  warning when hit.
- `SUPPORT_MATRIX.md` rows for `defrule` and `defconstraint
  :backend :egg` flip from "stub" / "DROP" to "wired".
- Integration tests at
  `verifiers/osmotic_pressure/rust-verifier/tests/eqsat_*.rs`
  exercising a 3-rule rewrite set against a known-canonical
  fixture.

## Capabilities touched

- `eqsat` — ADD (new capability; egg-backed equality saturation)

## Implementation notes

See `docs/plans/2026-05-18-tier234-and-usefulness.md`, Phase G.

## Acceptance

- 7 REQ-EQSAT IDs ship in `specs/eqsat/spec.md`.
- `SUPPORT_MATRIX.md` no longer lists `defrule` or
  `defconstraint :backend :egg` as stub / DROP.
- A regression test asserts that omitting an algebraic rule
  changes a canonicalisation outcome.
- Saturation-budget warning fires deterministically on a fixture
  with a non-terminating rule.
