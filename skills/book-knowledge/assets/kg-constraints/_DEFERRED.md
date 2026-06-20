# Constraint coverage (P2.2)

booklogic `defconstraint` EDN files in this directory each lower (via
`scripts/booklogic_kg.compile_constraint`) to a CozoScript rule yielding
violation rows `[focus_node, path, message]`, reproducing the SHACL shapes in
`assets/shapes.ttl`. Each has a byte-identical compile golden under
`tests/golden/kg-constraints/<name>.cozoscript` and a live-Cozo execution test
in `tests/test_booklogic_constraint_compile.py`.

## Active constraints (7)

| EDN | SHACL shape ported | Mechanism |
| --- | --- | --- |
| `status-enum.edn` | `tbf:status` `sh:in` (5-value vocabulary) | five `!=` filters ANDed → status matches none |
| `confidence-range.edn` | `tbf:confidence` `sh:maxInclusive 1.0` | `:filter [[> ?conf 1.0]]` (the ceiling arm) |
| `confidence-range-low.edn` | `tbf:confidence` `sh:minInclusive 0.0` | `:filter [[< ?conf 0.0]]` (the floor arm — C-1; same `:message`/`:path` as the ceiling arm) |
| `text-cardinality.edn` | `schema:text` `sh:minCount 1` | free-var `:not` lifted to a `!is_null`-guarded helper rule |
| `source-span-present.edn` | `tbf:hasSourceSpan` `sh:minCount 1` | inline `:not` over the source-span back-ref |
| `verified-derives.edn` | `tbf:ClaimShape` `sh:sparql` | verified claim + `:not` source-span; message/path EXACT from the C0.2 golden |
| `chapter-cites-verified.edn` | `tbf:ChapterSectionShape` `sh:sparql` | section→claim join + `:filter [[!= ?status "verified"]]`; message/path EXACT from the C0.2 golden — **compiles + executes + active, but NO production data path (see below)** |

### Message parity note
pyshacl auto-generates the `sh:minCount` / range / `sh:in` messages (e.g.
"Less than 1 values ...", "Value is not <= Literal(\"1.0\", ...)"). The four
shape-generated constraints above carry a clear human message for P2.2; EXACT
pyshacl-message parity is a **P2.3** concern (the Cozo-backed `validate_shacl`
and its parity gate). Only `verified-derives` (the `sh:sparql` shape) has an
author-written `sh:message` in `shapes.ttl`, so its message/path are copied
verbatim and already match the C0.2 golden.

### confidence-range — BOTH arms ported (C-1 closed)
The `tbf:confidence` `sh:minInclusive 0.0 ; sh:maxInclusive 1.0` range is now
FULLY ported across two rules (the compiler has no `OR`/disjunction within one
rule): `confidence-range.edn` covers the ceiling (`confidence > 1.0`) and
`confidence-range-low.edn` covers the floor (`confidence < 0.0`). Both carry the
SAME authored `:message` (`Claim confidence must be in [0.0, 1.0].`) and the
SAME `:path` (`#confidence`), so the rdflib path's message-remap (keyed on the
SHACL path) stays unambiguous regardless of which arm fired.

Before C-1, only the ceiling arm existed, so a `confidence < 0.0` claim was
rdflib-non-conforming (pyshacl enforces both bounds) but Cozo-conforming —
opposite verdicts. The floor arm closes that gap: a below-zero confidence is now
non-conforming under BOTH engines
(`tests/test_constraint_ports.py::test_both_engines_flag_confidence_below_zero`).
The C0.1 violating fixture still injects only the ceiling case (`1.5`), so the
C0.2 violating golden stays at 4 violations (the floor arm clears on those rows).

## `chapter-cites-verified` — active but UNWIRED (no production data path)

The `tbf:ChapterSectionShape` (`sh:sparql`,
"Chapter sections must only cite verified claims.") shape was **deferred from
P2.2 to P2.3** because P2.2 had no schema home for it, then activated in P2.3
once `kg-schema.edn` gained a `:chapter-section` entity.

It is genuinely active in the engine — it **compiles** to a byte-identical
`.cozoscript` golden, it **executes** against a live store (a section citing a
non-verified claim fires; one citing a verified claim conforms), and it is in
`ACTIVE_CONSTRAINTS` so both backends run it on every validation.

**BUT it has NO production data path.** `project_ledger` loads
`:chapter-section` **EMPTY** — there is no projector that sources chapter→claim
citation data from a real workspace (the C0.1 fixture injected the
`tbf:ChapterSection` / `tbf:usesClaim` triples as raw RDF / synthetic store rows
only, with no ledger record behind them, like `chapter-wiki-ref` /
`rebuttal-window-ok`). Consequently:

- On a REAL workspace, `chapter-section` is always empty, so the join in the
  compiled rule has nothing to match and the constraint is a **guaranteed
  no-op** — it can never fire until a real `chapter-section` projector exists.
- It fires ONLY on **hand-loaded test rows** (the P2.3 violating parity test
  loads synthetic `chapter-section` rows directly into the store; the live
  execution test does the same).

Do **not** read this constraint as a fully-wired chapter-citation gate on
production data. Building a real `chapter-section` projector (sourcing citation
data from the workspace) is a **future task**; until then the shape compiles and
executes correctly but validates nothing on real workspaces.
