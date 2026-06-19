# Design: KG substrate hardening

## Harness

The conformance harness lives in `skills/book-knowledge/scripts/substrate_conformance.py`.
It reads committed fixture JSON files from
`skills/book-knowledge/tests/fixtures/substrate-conformance/`. Each fixture pins:

- a name
- an authored EDN query path under `assets/kg-queries/`
- a declared subset id
- relation rows to load through `CozoStore.load`
- expected rows for the frozen snapshot

For each fixture, the harness creates a fresh production store via
`CozoStore.in_memory`, loads the fixture rows through `load`, and runs the EDN
query through `query_edn`. It never reaches past `cozo_store` into `pycozo`.

## Reference evaluator

The reference evaluator lives in `skills/book-knowledge/scripts/reference_datalog.py`.
It is a pure-Python EDN evaluator for the declared `defquery-basic-v1` subset:

- `defquery` forms only
- plain variable `:find` terms
- `:where` entity/attribute triples
- joins by shared variables and shared entity variables
- literal equality
- ordered `:filter` comparisons over bound variables
- safe `:not` groups

It explicitly does not cover aggregation, constraints, recursive `defrules`, or
argumentation/contradiction rule programs. Fixtures outside this subset are not
dual-run. This is deliberate: the reference backend must be an honest evaluator
for a small surface, not a fake claim of full coverage.

The evaluator parses the EDN query and evaluates relation rows directly. It does
not call the compiler, Cozo, `CozoStore`, or `pycozo`, so equality with Cozo is a
real independent cross-check rather than an echo.

## Authoring-time only

The reference evaluator is not a `Backend` implementation and is never registered
with `CozoStore`. The production path remains `CozoStore.in_memory`, which
constructs a `CozoBackend` inside `cozo_store.py`. REQ-KG-002 and REQ-KG-002b
remain unchanged: Cozo is the sole production store, and only `cozo_store.py`
imports `pycozo`.

## Canonical ordering

Result rows are compared as multisets. Each row is encoded as compact JSON and
sorted lexicographically; duplicate rows are preserved through a `Counter` for
the equality check. The canonical JSON serialization is stable regardless of
backend emission order.

## Divergence

If Cozo and the reference evaluator differ, the harness raises
`SubstrateDivergenceError` with the fixture name and the symmetric difference:
`cozo_only` rows and `reference_only` rows. A fixture expected-row mismatch also
fails loudly, naming actual and committed expected rows.

## Switch triggers

The substrate trigger list is documented in
`docs/operations/kg-substrate-switch-triggers.md`. The four triggers are:

- Python or platform support breaks.
- An unpatchable correctness or security issue appears.
- The reference backend reproduces the rule surface acceptably.
- The embedded / Python-primary / offline constraints are relaxed.

These triggers open a future design decision; they do not perform a migration.
