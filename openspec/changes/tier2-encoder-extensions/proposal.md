# Change: tier2-encoder-extensions

**Tier:** 2 of 4 (general-purpose framework hardening)
**Branch:** `feat/tier2-encoder-extensions`
**Depends on:** none (independent of E.1 and E.3)

## Why

`skills/neurosym-forge/scripts/codegen_axioms.py::_emit_z3_block`
currently accepts only `=`, `*`, `+`, `approx=`, `and`, `or` as assert
heads (line ~166 today). Every other binary operator — `<`, `<=`,
`>`, `>=`, `/`, conditional `ite` — is a hard codegen error:

```
constraint :temperature-window: assert head '<' not supported in v0.4
(use '=' or 'approx=')
```

That is enough operator coverage for the two shipping verifiers
(osmotic pressure is one `approx=` equality; bermuda is structural
equality only). It is *not* enough for the framework's third use case
on deck: a temperature-bounded-reaction toy verifier needs
`(< :temperature-k :upper-bound)`; a price-floor constraint needs
`(>= :unit-price :floor)`; a tax-bracket constraint needs an `ite`.

Worked example we want to make legal:

```edn
(defconstraint :thermal-window
  :assert (and (< (:temperature-k ?s) 333.15)
               (> (:temperature-k ?s) 273.15)))
```

Today this hits the v0.4 error. With this change the codegen translates
the form to:

```rust
solver.assert_and_track(
  &Bool::and(&[
    &Real::lt(&Real::new_const("temperature-k_s"), &Real::from_rational_str("33315","100").unwrap()),
    &Real::gt(&Real::new_const("temperature-k_s"), &Real::from_rational_str("27315","100").unwrap()),
  ]),
  &Bool::new_const("c-thermal-window-of-s"),
);
```

## What

Extend `_emit_z3_block` (and the underlying `_emit_expr_typed`) to handle
six new assert heads: `<`, `<=`, `>`, `>=`, `/`, `ite`. The dispatch
table maps each to a Z3 Rust API method (`lt`, `le`, `gt`, `ge`,
`div`, `ite`). Unknown heads still fail at codegen time, but the
failure message now enumerates the supported set so authors know what is
available.

`docs/booklogic-dsl-reference.md` § 2.5 (`defconstraint`) gets the
expanded operator list as authored prose.

## Capabilities touched

- `verifier-build` — MODIFY (extends the codegen operator surface)

## Implementation notes

See `docs/plans/2026-05-18-tier234-and-usefulness.md`, Phase E.2.

## Acceptance

- A `defconstraint` form using `<`, `<=`, `>`, `>=`, `/`, or `ite`
  codegens to valid Rust and the resulting verifier compiles + runs.
- An unknown operator (`(defconstraint :foo :assert (mod ?x 5))`) fails
  at codegen with an error listing the supported set.
- The DSL reference enumerates the full operator set in § 2.5.
