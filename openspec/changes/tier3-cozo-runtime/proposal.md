# Change: tier3-cozo-runtime

**Tier:** 3 of 4 (promote a wired-builder backend to wired)
**Branch:** `feat/tier3-cozo-runtime`
**Depends on:** Tier 1 (binding-schema)

## Why

`SUPPORT_MATRIX.md` flags `defquery` as **wired-builder** —
`codegen_kg.py` produces a valid Cozo-driven `kg.rs`, but
`npm run build` does not actually run the queries at smoke time.
External consumers (`book-qa`) read the generated module, but
the verifier's own verdict never reflects any `defquery`
result. `defconstraint :backend :cozo` is flagged **DROP**
for the same reason `:egg` is: `codegen_axioms.py:139` silently
skips non-`:z3` backends. `defremedy` is flagged **external** —
remedies compile to declarative EDN but cannot bind a query's
result rows into their `:propose` action surface.

Authors who write Datalog queries today observe nothing in the
verifier's verdict. The DSL appears to support Datalog; the
runtime does not surface it.

## What

- Wire the Cozo runtime into `make ci` via the verifier binary:
  each `defquery` in `rules/queries.edn` is run during the
  smoke step, results are persisted to `work/query-results.edn`.
- The combined verdict gains a `:queries [...]` field listing
  every query name that returned at least one row.
- `defconstraint :backend :cozo` routes to Cozo Datalog
  evaluation; its verdict is merged with Z3's into a unified
  defect surface.
- `defremedy` forms whose `:when` clause references a
  `defquery` name receive the query's result rows bound into
  their `:propose` action.
- A `VERIFIER_DATALOG_TIMEOUT_MS` (default 10000) cap, with
  `:datalog-timeout` surfacing on the verdict.
- `SUPPORT_MATRIX.md` rows for `defquery`, `defconstraint
  :backend :cozo`, and `defremedy` (query-bound case) all flip
  to `wired`.

## Capabilities touched

- `datalog` — ADD (new capability; Cozo-backed query +
  constraint + remedy binding surface)

## Implementation notes

See `docs/plans/2026-05-18-tier234-and-usefulness.md`, Phase H.

## Acceptance

- 6 REQ-DATALOG IDs ship in `specs/datalog/spec.md`.
- `make ci` invokes the Cozo runtime and a query that returns
  rows surfaces them on the verdict.
- A `:datalog-timeout` entry fires deterministically on a
  fixture with a deliberately slow query.
- `SUPPORT_MATRIX.md` no longer lists `defquery` as
  wired-builder, `:cozo` as DROP, or `defremedy` as external
  for the query-bound subset.
