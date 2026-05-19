# Design: booklogic-v0.5-boolean-quantifiers

## Architecture pointer

Full TDD-shaped detail at `docs/plans/2026-05-18-booklogic-v0.5-extended-operators.md`.

## Dispatch extension

`_emit_z3_block` (the assert-head dispatcher in `codegen_axioms.py`) gains six new
arms immediately after the `ite` arm added in PR #80:

1. `and` — variadic (2+ children)
2. `or` — variadic (2+ children)
3. `not` — unary
4. `=>` — binary
5. `forall` — binary `(bindings, body)`
6. `exists` — binary `(bindings, body)`

A new helper `_emit_bool_subexpr(node, bound_vars=None)` is extracted. It
dispatches on the same heads as `_emit_z3_block` (`=`, `~=`/`approx=`, `<`, `<=`,
`>`, `>=`, `ite`, and now all six new heads) and returns the Bool-typed Rust
expression *without* `assert_and_track`. Boolean arms call `_emit_bool_subexpr`
recursively for children. Quantifier arms call it for the body, threading
`bound_vars`.

## Z3 Rust API signatures

```rust
// Boolean connectives (z3::ast::Bool)
Bool::and(ctx, &[&a, &b, ...])       // REQ-SMT-046
Bool::or(ctx,  &[&a, &b, ...])       // REQ-SMT-047
<expr>.not()                          // REQ-SMT-048
<premise>.implies(&<conclusion>)      // REQ-SMT-049

// Quantifiers (z3::Context)
ctx.mk_forall_const(&[&bound_a.clone().into(), ...], &body, &[], &[], &[], &[])  // REQ-SMT-051
ctx.mk_exists_const(&[&bound_a.clone().into(), ...], &body, &[], &[], &[], &[])  // REQ-SMT-052

// Bound constant construction (z3::ast::Datatype)
Datatype::new_const(ctx, "?var_name", &sort_const)   // REQ-SMT-053, REQ-SMT-054
```

The empty slice arguments to `mk_forall_const` / `mk_exists_const` are pattern
triggers, weights, quantifier IDs, and comment IDs. All deferred to Tier 5 (Trigger
pattern annotations). v0.5 emits all four as `&[]` and relies on Z3's MBQI solver.

The `Datatype` import is appended to the `use z3::ast::{...}` line in whatever
preamble template `codegen_axioms.py` emits; the exact preamble location is probed
in Task 1 Step 5 of the plan.

## `bound_vars` threading

`bound_vars: dict[str, str]` maps EDN `?var` symbol strings to the Rust identifier
of the corresponding `Datatype` constant (e.g. `"?o" -> "o_const"`). It is threaded
as an optional keyword parameter (default `None`) through three helpers:

```python
_emit_expr(node, bound_vars=None)
_emit_expr_typed(node, z3_type, bound_vars=None)
_emit_bool_subexpr(node, bound_vars=None)
```

Inside `_emit_expr`, when a `Symbol` whose name starts with `?` appears:

```python
if name.startswith("?"):
    if not bound_vars or name not in bound_vars:
        raise CodegenError(
            f"unbound variable {name!r} (not in any forall/exists scope)"
        )
    return bound_vars[name]
```

The default `None` preserves the behaviour of all existing call sites — no changes
to existing constraints are required. Each quantifier arm builds its own `bound_vars`
dict and passes it when recursing into the body; no global mutation.

## Sort-registry validation hook

`generate_axioms_source(constraints, sorts)` builds `declared_sort_names` (a
`set[str]`) at its top before any constraint is processed:

```python
declared_sort_names = {
    (s[Keyword("name")].name
     if hasattr(s[Keyword("name")], "name")
     else str(s[Keyword("name")]))
    for s in sorts
    if isinstance(s, dict) and Keyword("name") in s
}
```

This set is made available inside `_emit_z3_block` (via parameter or closure). When
a quantifier binding names a sort keyword, the sort name is checked against
`declared_sort_names` before the `Datatype` constant is emitted. An undeclared sort
raises `CodegenError: sort '...' not declared in sorts.edn`. This check fires at
Python codegen time, not at Rust compile time, giving immediate feedback.

## Backward-compatibility guarantee

The six new arms are only reached when the assert head is one of `and`, `or`, `not`,
`=>`, `forall`, `exists`. No existing constraint uses these heads. As a result:

- The bermuda verifier's `axioms.rs` is byte-identical before and after the merge.
- The osmotic_pressure verifier's `axioms.rs` is byte-identical before and after the merge.
- A deterministic-output pin test (Task 6 step 1 of the plan) asserts this before the
  PR is opened.

No migration, no recompilation, no constraint rewriting is needed for existing
BookLogic projects.

## Pre-declared split

No track split anticipated. All six heads are additive (new `if head ==` arms in a
shared function). The only sequencing constraint is Tasks 1 → 2 → 3 → 4 (each
builds on the shared dispatcher). Tasks 5 and 6 are independent of each other and
run after Task 4.
