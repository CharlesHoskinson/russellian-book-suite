# BookLogic v0.4 Support Matrix

> Single source of truth for which DSL form / backend combinations are
> actually wired vs claimed. Drift from `codegen_axioms.py` is caught
> by `tests/test_support_matrix.py` (REQ-BOOKLOGIC-049, 050).

## Form-family matrix

| Form family                  | CLJS compile | Codegen path        | Solver       | Status |
|------------------------------|--------------|---------------------|--------------|--------|
| `defsort`                    | wired        | (validation only)   | n/a          | wired  |
| `defpredicate`               | wired        | (validation only)   | n/a          | wired  |
| `deflift`                    | wired        | `predicates.edn`    | n/a          | wired  |
| `defrule`                    | wired        | none                | egg          | stub   |
| `defconstraint :backend :z3` | wired        | `codegen_axioms.py` | Z3           | wired  |
| `defconstraint :backend :egg`| wired        | none (silent drop)  | egg          | DROP   |
| `defconstraint :backend :cozo` | wired      | none (silent drop)  | Cozo         | DROP   |
| `defquery`                   | wired        | `codegen_kg.py`     | Cozo         | wired-builder |
| `defremedy`                  | wired        | none                | n/a          | external |

## Status legend

**wired** — Full end-to-end path: CLJS expand → codegen → solver/runtime → verdict surface.
A defconstraint :backend :z3 form is asserted in Z3, included in unsat-core
reporting, and surfaces as a defect entry in `verification-defects.json`.

**stub** — The form is recognised by the CLJS expander and stored in the
intermediate registry, but no downstream codegen consumes it. Adding the form
is a no-op at solver time. Tier 3 of the framework roadmap promotes egg from
stub to live (REQ-EQSAT-* — not yet authored). Authors writing `defrule`
forms today should not expect them to influence the verdict.

**DROP** — The form is recognised AND in `SUPPORTED_BACKENDS` AND passes the
codegen validation gate, but `codegen_axioms.py:138` silently `continue`s on
non-`:z3` backends. The constraint is omitted from the Z3 input. The verdict
is `:sat` for the wrong reason (the constraint that would have made it `:unsat`
was never asserted). Tier 4 of the framework roadmap promotes egg/cozo
constraints to first-class.

**wired-builder** — Codegen produces output but it's not consumed by
`npm run build` by default. `defquery` forms compile via `codegen_kg.py` to
Cozo-compatible rule sources, but the verifier's `npm run build` doesn't
run the queries during smoke. External consumers (book-qa) wire the queries.

**external** — The form compiles to a declarative entry in an intermediate
EDN file consumed exclusively by an outside-the-verifier component
(`book-qa`). `defremedy` outputs do not change the verifier's verdict;
they're a proposed action surface that book-qa reads on `:unsat`.

## Why this exists

Earlier iterations of the skill described `:egg` and `:cozo` as supported
backends without flagging the silent-drop behaviour. Authors wrote
constraints with those backends, observed `:sat` verdicts, and concluded
the framework had validated their claims — when in fact the constraint
had been dropped. SUPPORT_MATRIX.md + the drift lint
(`test_support_matrix.py`) keep the doc-vs-code state synchronised.

## Roadmap pointers

- Tier 3: promote egg from stub → live (eqsat-driven canonicalisation
  consumed by codegen_axioms before Z3 sees the formula)
- Tier 4: promote `:egg` / `:cozo` constraint backends from DROP → wired
  (separate solver invocations integrated into the verdict)
- Tier 2: stop the silent JS-to-Python regex converter in `_to_python_regex`
  — surface JS-style `(?<v>)` as a hard error
