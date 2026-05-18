# Design: tier2-encoder-extensions

## Operator → Z3 Rust API mapping

The expansion is mechanical: `_emit_z3_block` already infers a Z3 type
from RHS shape; the new heads slot into the same dispatch with a
per-operator Rust method name.

| Assert head      | Z3 method (Real)            | Z3 method (Int)             | Result type | Operand arity |
|------------------|-----------------------------|------------------------------|-------------|---------------|
| `<`              | `Real::lt(&a, &b)`          | `Int::lt(&a, &b)`            | `Bool`      | 2             |
| `<=`             | `Real::le(&a, &b)`          | `Int::le(&a, &b)`            | `Bool`      | 2             |
| `>`              | `Real::gt(&a, &b)`          | `Int::gt(&a, &b)`            | `Bool`      | 2             |
| `>=`             | `Real::ge(&a, &b)`          | `Int::ge(&a, &b)`            | `Bool`      | 2             |
| `/`              | `Real::div(&a, &b)`         | `Int::div(&a, &b)`           | numeric     | 2             |
| `ite`            | `Bool::ite(&cond, &t, &e)`  | `Bool::ite(&cond, &t, &e)`   | branch type | 3             |

The Real-vs-Int branch is chosen by `_subtree_has_float` on the operand
subtrees, mirroring the existing logic for `approx=`. `Int::div` is
present in z3-rs 0.20 and matches the SMT-LIB `div` semantics
(truncation toward negative infinity for negative dividend).

## `ite` typing

`ite` is the only ternary operator. Its first argument is `Bool`, its
second and third must be of the same Z3 sort. The codegen infers the
branch sort from the type of the `then-expr`:

```
(ite (< ?x 0) (- ?x) ?x)
  → Real::ite(&Real::lt(&x, &Real::from_rational_str("0","1")?),
              &Real::neg(&x),
              &x)
```

For string-typed branches the result is `Z3String::ite`.

## Unknown-head failure message

Today:

```
constraint :foo: assert head 'mod' not supported in v0.4 (use '=' or 'approx=')
```

Tomorrow:

```
constraint :foo: assert head 'mod' not supported. Supported heads:
  =, approx=, ~=, +, -, *, /, <, <=, >, >=, and, or, ite
See docs/booklogic-dsl-reference.md § 2.5.
```

The enumerated list is sourced from a module-level
`_SUPPORTED_ASSERT_HEADS` tuple so it stays in sync with the dispatch
table.

## Test fixture shape

New tests live in
`skills/neurosym-forge/scripts/tests/test_codegen_axioms_operators.py`.
Each test:

1. Constructs an EDN assert form via `read_edn(...)`.
2. Calls `_emit_z3_block` and asserts the emitted Rust string contains
   the expected method call (`Real::lt`, `Bool::ite`, etc.).
3. Where possible, the Rust output is fed to a tiny `cargo check` shim
   in `tests/fixtures/codegen-smoke/` to confirm it parses.

## Why Real `div`, not `RealDiv` SMT-LIB primitive?

z3-rs 0.20 exposes `Real::div` which translates to the SMT-LIB
`(/ a b)` op directly. There is no `RealDiv` primitive — the
SMT-LIB-1.2 form `/` is the canonical name and Z3 implements it via
`Real::div`. The dispatch table is one-line per operator.

## Why not extend in CLJS first?

The CLJS compiler already accepts any list head in `:assert` and
emits it verbatim into the EDN — the operator strings flow through
without CLJS-side dispatch. The codegen is the only consumer that
performs the operator → API call lowering. Authoritative dispatch
lives at the codegen layer.
