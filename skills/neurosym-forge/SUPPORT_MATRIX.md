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
| `defconstraint :backend :cozo` | wired      | `codegen_axioms.py` | Cozo         | wired  |
| `defquery`                   | wired        | `codegen_kg.py`     | Cozo         | wired  |
| `defremedy`                  | wired        | `verdict_to_qa.py`  | n/a          | wired (query-bound) |

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
codegen validation gate, but the dispatch loop in `codegen_axioms.py`
silently `continue`s on the unsupported branch. The constraint is omitted
from every solver's input. The verdict is `:sat` for the wrong reason (the
constraint that would have made it `:unsat` was never asserted). After
Tier 3 only `:egg` constraints remain DROP'd; `:cozo` is now routed to
`kg::evaluate_constraint`. Tier 4 of the framework roadmap promotes `:egg`
constraints to first-class.

**external** — Remedies whose `:when` clause does NOT reference a
`defquery` still flow through the existing book-qa hook
(`propose_writeback.py`). The verdict surface does not gate them; they
are advisory actions read after `:unsat`. Remedies whose `:when` DOES
reference a defquery flow through the Tier 3 query-bound path (see
`wired (query-bound)` below).

**wired (query-bound)** — A `defremedy` whose `:when {:query :Q###}`
references a `defquery` name receives the query's row count bound into
its `:propose` action surface by `verdict_to_qa.py`. The remedy entry
in `verification-defects.json` carries `query_bound=true` and the
materialised row count.

## Why this exists

Earlier iterations of the skill described `:egg` and `:cozo` as supported
backends without flagging the silent-drop behaviour. Authors wrote
constraints with those backends, observed `:sat` verdicts, and concluded
the framework had validated their claims — when in fact the constraint
had been dropped. SUPPORT_MATRIX.md + the drift lint
(`test_support_matrix.py`) keep the doc-vs-code state synchronised.

## Roadmap pointers

- Tier 3 (this change): promote `defquery` from wired-builder → wired,
  `defconstraint :backend :cozo` from DROP → wired, and query-bound
  `defremedy` from external → wired. Tracked in
  `openspec/changes/tier3-cozo-runtime/`.
- Tier 3 follow-on: promote egg from stub → live (eqsat-driven
  canonicalisation consumed by codegen_axioms before Z3 sees the formula).
- Tier 4: promote `:egg` constraint backends from DROP → wired (separate
  solver invocations integrated into the verdict).
- Tier 2: stop the silent JS-to-Python regex converter in
  `_to_python_regex` — surface JS-style `(?<v>)` as a hard error.
