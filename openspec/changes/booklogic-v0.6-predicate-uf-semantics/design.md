# Design: booklogic-v0.6-predicate-uf-semantics

## Problem recap

`_emit_bool_subexpr` (`codegen_axioms.py:1289-1300`) lowers a Keyword-headed
predicate to a name-encoded opaque Bool:

```python
if isinstance(head_node, Keyword):
    pred = head_node.name
    arg_parts = [...]            # ?a -> "a", :Subject -> "Subject"
    var_name = "_".join([pred] + arg_parts).replace("-", "_")
    return f'Bool::new_const("{var_name}")'
```

`Bool::new_const("contradicts_a_b")` is a nullary Bool. The bound `?a`/`?b`
constants created in `_emit_quantifier_expr` never reach it, so under
`forall a, b. ...contradicts_a_b...` the body is constant in `a, b` and the
quantifier proves nothing about the predicate.

## Target encoding

Declare each Bool-returning predicate as a Z3 uninterpreted function and apply it
to the resolved argument constants.

```rust
// preamble (emitted once)
let contradicts_fn = FuncDecl::new(
    "contradicts",
    &[&obligation_sort, &obligation_sort],   // from schema :arg-sorts
    &Sort::bool(),                            // from schema :return
);

// at the predicate application site, inside the quantifier body
contradicts_fn.apply(&[&a_const, &b_const]).as_bool().unwrap()
```

`FuncDecl::apply` returns `Dynamic`; `.as_bool().unwrap()` narrows it to `Bool`
so it composes with the existing `.implies(...)`, `Bool::and(...)`, `.not()`
combinators unchanged. Two applications of the same `FuncDecl` to the same args
are the *same* Z3 term, so the quantifier now binds them.

## Where the pieces live

### 1. Registry build — `generate_axioms_source`

The schema is already parsed into `_SCHEMA` (the `:predicates` map). Add, next to
the `declared_sort_names` build (lines 291-298), a predicate-UF registry:

```python
predicate_ufs: dict[str, dict] = {}   # name -> {arg_sorts: [str], return: str}
for pred_kw, spec in (_SCHEMA or {}).items():
    arg_sorts = spec.get(Keyword("arg-sorts"))
    ret = spec.get(Keyword("return"))
    if arg_sorts and _is_bool_sort(ret):
        predicate_ufs[_kw_name(pred_kw)] = {
            "arg_sorts": [_kw_name(s) for s in arg_sorts],
            "return": "bool",
        }
```

`arg_sorts` falsy (`nil`/empty) → predicate stays nullary → opaque-Bool path
(backward compat, REQ-SMT-061). Thread `predicate_ufs` down through `_emit_z3_block`
→ `_emit_bool_subexpr` / `_emit_quantifier_expr` alongside `declared_sort_names`
(same plumbing pattern).

### 2. Preamble emission

Add a helper analogous to the sort declarations in `_emit_quantifier_expr`. Because
`FuncDecl::new` of the same name+sig returns the same Z3 decl under the thread-local
context (same property the code already relies on for `Sort::uninterpreted`), the
declarations can be emitted into the same `{ ... }` block scope as the quantifier's
sort/const decls — no module-global preamble required, no cross-block leakage:

```python
fn_decls = []
for pred, sig in needed_ufs.items():
    sorts = ", ".join(f"&{_sort_const(s)}" for s in sig["arg_sorts"])
    fn_decls.append(
        f'let {pred}_fn = FuncDecl::new('
        f'{json.dumps(pred)}, &[{sorts}], &Sort::bool());'
    )
```

Each arg sort reuses the `let <sort>_sort = Sort::uninterpreted(...)` constant the
quantifier block already declares; primitive sorts (`:int`/`:real`/`:bool`/
`:string`) map to `Sort::int()`/`Sort::real()`/`Sort::bool()`/`Sort::string()`.
The `_sort_const` helper centralises primitive-vs-uninterpreted resolution and is
shared with the bound-constant declarations so the two never disagree.

### 3. Application emission — `_emit_bool_subexpr` keyword arm

```python
if isinstance(head_node, Keyword):
    pred = head_node.name
    if pred in predicate_ufs:
        sig = predicate_ufs[pred]
        args = list(node)[1:]
        if len(args) != len(sig["arg_sorts"]):
            raise CodegenError(
                f"predicate {pred!r} arity mismatch: schema declares "
                f"{len(sig['arg_sorts'])}, got {len(args)}")
        arg_refs = [_resolve_pred_arg(a, sig_sort, bound_vars, declared_sort_names)
                    for a, sig_sort in zip(args, sig["arg_sorts"])]
        joined = ", ".join(f"&{r}" for r in arg_refs)
        return f'{pred}_fn.apply(&[{joined}]).as_bool().unwrap()'
    # ... existing opaque-Bool fallback for nullary predicates (unchanged)
```

`_resolve_pred_arg`: a `?var` resolves to `bound_vars[str(var)]` (raise
`unbound variable` if absent — reuses the existing bound-var contract); a sort-typed
subject keyword resolves to a `Dynamic::new_const(name, &sort)` matching the
declared arg-sort; an arg whose value can't match the declared sort raises
`CodegenError: predicate '...' sort mismatch` (REQ-SMT-059).

## Determinism guarantee (REQ-SMT-061)

The three shipped verifiers declare every predicate with `:arg-sorts nil`
(confirmed: `verifiers/epidemiology/rules/booklogic-schema.edn` — all three
predicates are `{:arg-sorts nil, :return nil}`). The registry skips nil-arity
predicates, so their emission path is the untouched `Bool::new_const(...)` branch.
The byte-identical check is a regression pin: generate `axioms.rs` for bermuda +
osmotic_pressure on the base commit, regenerate after the change, assert equal.

## Soundness test (REQ-SMT-060)

A synthetic schema declares `obligation` sort and `contradicts`/`supersedes` as
`{:arg-sorts [:obligation :obligation], :return :bool}`. Two constraints:

- **Entailed:** assert a witness `(:contradicts :A :B)` and
  `(forall [(?a :obligation)(?b :obligation)] (=> (:contradicts ?a ?b) false))` —
  contradictory ⇒ Z3 returns `:unsat`. The opaque-Bool encoder returns `:sat`
  (distinct Bools), so this case *fails before the fix and passes after* — the
  test that proves soundness.
- **Non-entailed:** drop the witness ⇒ `:sat`.

Run via the codegen → cargo path on a scratch verifier, gated behind the same
`--features smt` CI leg the v0.5 acceptance used. The fast unit layer asserts the
emitted Rust contains `contradicts_fn.apply(` rather than `Bool::new_const(`.

## Why not declare UFs in a module-global preamble?

The partitioned axiom surface (`axioms_for_subject`/`axioms_shared`/`axioms_corpus`)
emits independent `solver.assert(...)` blocks. A module-global `FuncDecl` would have
to be created in each function's context anyway. Emitting block-locally — exactly as
`Sort::uninterpreted` is handled today — keeps the same-symbol-under-thread-local-ctx
invariant the codebase already documents and avoids a second sharing mechanism.

## Risk

- **z3 0.20 `FuncDecl` API surface.** `FuncDecl::new(name: impl Into<Symbol>,
  domain: &[&Sort], range: &Sort)` and `apply(&[&dyn Ast]) -> Dynamic` are the
  0.20 signatures. Validated by the `cargo check --features smt` leg, not locally
  (Windows libz3 link is a known skip; CI canonical is ubuntu).
- **Blast radius:** behind the registry gate. No registry entry (today's verifiers)
  ⇒ no behaviour change. Only verifiers that declare arg-sorted Bool predicates
  exercise the new path.
