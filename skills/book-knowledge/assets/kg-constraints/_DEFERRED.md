# Constraint coverage (P2.2)

booklogic `defconstraint` EDN files in this directory each lower (via
`scripts/booklogic_kg.compile_constraint`) to a CozoScript rule yielding
violation rows `[focus_node, path, message]`, reproducing the SHACL shapes in
`assets/shapes.ttl`. Each has a byte-identical compile golden under
`tests/golden/kg-constraints/<name>.cozoscript` and a live-Cozo execution test
in `tests/test_booklogic_constraint_compile.py`.

## Active constraints (6)

| EDN | SHACL shape ported | Mechanism |
| --- | --- | --- |
| `status-enum.edn` | `tbf:status` `sh:in` (5-value vocabulary) | five `!=` filters ANDed → status matches none |
| `confidence-range.edn` | `tbf:confidence` `sh:maxInclusive 1.0` | `:filter [[> ?conf 1.0]]` (the `< 0.0` arm is out of scope — see below) |
| `text-cardinality.edn` | `schema:text` `sh:minCount 1` | free-var `:not` lifted to a `!is_null`-guarded helper rule |
| `source-span-present.edn` | `tbf:hasSourceSpan` `sh:minCount 1` | inline `:not` over the source-span back-ref |
| `verified-derives.edn` | `tbf:ClaimShape` `sh:sparql` | verified claim + `:not` source-span; message/path EXACT from the C0.2 golden |
| `chapter-cites-verified.edn` | `tbf:ChapterSectionShape` `sh:sparql` | section→claim join + `:filter [[!= ?status "verified"]]`; message/path EXACT from the C0.2 golden |

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

## Activated in P2.3: `chapter-cites-verified`

The 6th SHACL shape — `tbf:ChapterSectionShape` (`sh:sparql`,
"Chapter sections must only cite verified claims.") — was **deferred from P2.2
to P2.3** because P2.2 had no schema home for it:

1. **No schema entity (now resolved).** P2.2's `kg-schema.edn` declared no
   `chapter-section` entity. P2.3 added a `:chapter-section` entity
   (`:attrs [:id :uses-claim-id]`, `[:cites :claim]` relation), so the
   `defconstraint` now references only declared entities/attrs and compiles to a
   byte-identical golden + a live-execution test like the other five.

2. **No production data source (still future work).** In the C0.1 violating
   fixture the `tbf:ChapterSection` / `tbf:usesClaim` triples were injected as
   **raw RDF only** — no ledger record sits behind them. `project_ledger`
   therefore loads `:chapter-section` **empty** (like `chapter-wiki-ref` /
   `rebuttal-window-ok`), which keeps the bermuda workspace at 0 violations. The
   P2.3 violating parity test loads synthetic `chapter-section` rows directly
   into the store. A **real chapter-section projector** (sourcing citation data
   from the workspace) is a follow-on task; the constraint is correct and active
   now, it simply has no production rows to validate yet.
