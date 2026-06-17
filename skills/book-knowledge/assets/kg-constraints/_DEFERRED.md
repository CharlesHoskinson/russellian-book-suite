# Constraint coverage (P2.2)

booklogic `defconstraint` EDN files in this directory each lower (via
`scripts/booklogic_kg.compile_constraint`) to a CozoScript rule yielding
violation rows `[focus_node, path, message]`, reproducing the SHACL shapes in
`assets/shapes.ttl`. Each has a byte-identical compile golden under
`tests/golden/kg-constraints/<name>.cozoscript` and a live-Cozo execution test
in `tests/test_booklogic_constraint_compile.py`.

## Active constraints (5)

| EDN | SHACL shape ported | Mechanism |
| --- | --- | --- |
| `status-enum.edn` | `tbf:status` `sh:in` (5-value vocabulary) | five `!=` filters ANDed → status matches none |
| `confidence-range.edn` | `tbf:confidence` `sh:maxInclusive 1.0` | `:filter [[> ?conf 1.0]]` (the `< 0.0` arm is out of scope — see below) |
| `text-cardinality.edn` | `schema:text` `sh:minCount 1` | free-var `:not` lifted to a `!is_null`-guarded helper rule |
| `source-span-present.edn` | `tbf:hasSourceSpan` `sh:minCount 1` | inline `:not` over the source-span back-ref |
| `verified-derives.edn` | `tbf:ClaimShape` `sh:sparql` | verified claim + `:not` source-span; message/path EXACT from the C0.2 golden |

### Message parity note
pyshacl auto-generates the `sh:minCount` / range / `sh:in` messages (e.g.
"Less than 1 values ...", "Value is not <= Literal(\"1.0\", ...)"). The four
shape-generated constraints above carry a clear human message for P2.2; EXACT
pyshacl-message parity is a **P2.3** concern (the Cozo-backed `validate_shacl`
and its parity gate). Only `verified-derives` (the `sh:sparql` shape) has an
author-written `sh:message` in `shapes.ttl`, so its message/path are copied
verbatim and already match the C0.2 golden.

### confidence-range — single arm only
`confidence-range.edn` covers only `confidence > 1.0` (`sh:maxInclusive`). The
C0.1 violating fixture injects exactly one out-of-range value (`1.5`), so this
single rule reproduces the C0.2 golden. The `sh:minInclusive 0.0` arm
(`confidence < 0.0`) needs a SECOND rule (the compiler has no `OR`/disjunction
within one rule); add it in a later task when a fixture exercises it.

## Deferred: `chapter-cites-verified` (-> P2.3)

The 6th SHACL shape — `tbf:ChapterSectionShape` (`sh:sparql`,
"Chapter sections must only cite verified claims.") — is **NOT** authored here.
It is deferred to **P2.3** for two structural reasons:

1. **No schema entity.** `assets/kg-schema.edn` declares NO `chapter-section`
   entity and NO `uses-claim` (chapter→claim citation) relation. A
   `defconstraint` can only reference entities/attrs declared in the schema (the
   compiler raises `ValueError` otherwise), so the constraint cannot be expressed
   today. P2.3 must first add a `chapter-section` entity (with a `uses-claim`
   back-reference) to `kg-schema.edn` plus a projector that populates it.

2. **No Cozo data source.** In the C0.1 violating fixture the
   `tbf:ChapterSection` / `tbf:usesClaim` triples were injected as **raw RDF
   only** — there is no ledger record or Cozo relation behind them. Even with a
   schema entity, the Cozo validation path would have nothing to validate until
   P2.3 decides WHERE chapter-section citation data is sourced from (the
   violating fixture's chapter data lives only in the RDF graph, not the ledger).

Authoring a non-compiling chapter EDN now would break the byte-identical-golden
and live-execution contracts, so it is intentionally omitted until P2.3 supplies
the entity, projector, and data source.
