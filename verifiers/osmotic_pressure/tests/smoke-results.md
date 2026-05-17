# Osmotic-pressure smoke results

## Local build (Windows, 2026-05-17)

Local `cargo build --features smt` failed on Windows due to Int/Real type
mismatch in generated `axioms.rs`: the codegen emits `Int::new_const(...)` for
predicate accesses but the van 't Hoff RHS includes `Real::from_rational(8.314)`
(float literal). Z3 Rust API does not support `.sub()` across Int and Real sorts.

This is OQ#5 per the sprint-5 plan: local Windows cargo build is not the gate.
CI `osmotic-pressure-smoke` on `ubuntu-latest` is canonical. A follow-up should
fix the `_emit_expr` emitter to detect float-containing sub-expressions and
emit `Real::new_const` instead of `Int::new_const` for predicate accesses.

Error tail:
```
error[E0599]: no method named `sub` found for struct `z3::ast::Int` in the current scope
  --> src/axioms.rs:28:24
   |
28 |         let diff = lhs.sub(&rhs);
```
