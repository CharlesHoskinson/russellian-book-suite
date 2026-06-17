# KG SHACL representation divergence — canonical decision (P2.3, REQ-KG-017 pattern)

Date: 2026-06-17
Task: P2.3 — Cozo-backed `validate_shacl` + parity (REQ-KG-012/013)
Branch: `feat/homoiconic-kg-cutover`

## Context

P2.3 adds a `KG_BACKEND=cozo` path to
`skills/book-knowledge/scripts/validate_shacl.py`. It runs the
`assets/kg-constraints/*.edn` constraints (compiled by
`scripts.booklogic_kg.compile_constraint`) over a `CozoStore` and assembles the
SAME `ShaclReport` dataclass the existing pyshacl (rdflib) path produces. Default
stays `rdflib`; P5.3 flips the default at cutover.

For the two engines to be proven equivalent (REQ-KG-013), their violation sets
must be result-set equal on the C0.2 goldens — bermuda (conforms, 0 violations)
and the C0.1 violating fixture (non-conforming, 4 violations). But the raw
outputs differ in two structural ways, so a canonical representation must be
chosen (the REQ-KG-017 pattern: pick one semantics, update the golden, record
the decision).

## The two divergences

1. **focus_node spelling.** The rdflib path reports the FULL minted URI
   (`https://example.org/book-knowledge/claims/inj-bad-confidence`,
   `.../sections/inj-section`). The Cozo store keys claims/sections on their
   BARE ledger ids (`inj-bad-confidence`, `inj-section`) — there is no URI in the
   relational store.

2. **message wording.** pyshacl AUTO-GENERATES the messages for the shape-based
   constraints (range / minCount / `sh:in`), e.g.
   `Value is not <= Literal("1.0", datatype=xsd:decimal)` and
   `Less than 1 values on <...>->tbf:hasSourceSpan`. The booklogic EDN files
   carry hand-authored `:message` strings (`Claim confidence must be <= 1.0.`,
   `Claim must have at least one source-span (minCount 1 on hasSourceSpan).`).
   The two `sh:sparql` shapes (`verified-derives`, `chapter-cites-verified`)
   already carry an author-written `sh:message` in `shapes.ttl`, so pyshacl emits
   the SAME string the EDN does for those.

## Canonical representation (FINAL)

A violation's identity is `(focus_node, path, message)` where:

- **focus_node = bare claim/section id.** The rdflib path strips the
  `.../claims/` and `.../sections/` URI prefixes
  (`_strip_focus_uri`); the Cozo path already emits bare ids. The bare id still
  contains the injected marker (`inj-...`), so the existing characterization
  assertions that look for `"inj-..."` substrings still hold.

- **message = the authored EDN `:message`.** The EDN constraint files are the
  single source of truth. The rdflib path remaps each violation's message,
  keyed on its SHACL `:path`, to the authored EDN message
  (`_build_canonical_messages` reads the same `kg-constraints/*.edn` the Cozo
  path compiles). ONLY non-empty paths are remapped: the two `sh:sparql` shapes
  have an empty path and already emit their authored `sh:message` through
  pyshacl, so they are left untouched (and an empty-path key would collide
  between the two `sh:sparql` shapes). The substrings the existing tests assert
  (`"Verified claims must derive"`, `"Chapter sections must only cite verified
  claims"`) survive because those ARE the authored messages.

- **path = the SHACL path URI**, unchanged, or `""` for the two `sh:sparql`
  shapes (which carry no `sh:path`). The existing tests that assert
  `"confidence"` / `"hasSourceSpan"` substrings in the path still hold.

The violation list is sorted by `(focus_node, path, message)` before the report
is assembled, so the set is order-stable across engines.

## Why this is safe for callers

The public contract is `report.conforms` and `len(report.violations)`. The
downstream callers — `skills/book-compose/scripts/{preflight.py,
book_preflight.py, build_release_bundle.py}` — read ONLY those two. None inspects
`focus_node`, `path`, or `message`. So the canonical representation is invisible
to production callers; it exists purely so the rdflib and Cozo engines can be
proven result-set equal (the parity gate).

## Golden update

The C0.2 violating golden `tests/golden/kg/shacl_report_violating.json` is
UPDATED to the canonical form (bare-id focus_node + authored EDN messages + path
URIs / `""`), generated from the actual `_evaluate_constraints` output (not
hand-typed), byte-stable (`indent=2`, `sort_keys=True`, trailing `\n`, LF). The
bermuda golden `shacl_report_bermuda.json` is UNCHANGED (still conforms, 0
violations) — the chapter-section relation is loaded EMPTY by `project_ledger`,
so the new 6th constraint clears on bermuda.

## Parity proof (non-tautological)

`tests/test_constraint_ports.py::test_constraints_match_shacl_golden` asserts
three things against the SAME updated golden:

1. bermuda-via-projection: `_evaluate_constraints` over a real
   `project_ledger`-projected clean workspace → `[]` (== bermuda golden).
2. violating-via-loaded-rows: `_evaluate_constraints` over the synthetic rows
   mirroring the C0.1 fixture → the 4 canonical violations (== violating golden).
3. PARITY: the DEFAULT rdflib path over the same C0.1 fixture, normalized via
   `_normalize_pyshacl_violations`, → the same 4 violations (== violating
   golden).

So `rdflib(normalized) == golden == cozo` — both engines agree on the canonical
representation, not merely on the conforms flag.

## Post-audit status update (C-1 / I-3)

Two corrections from the 2026-06-17 adversarial audit of C0+P2:

- **Confidence range — now FULLY ported (C-1 closed).** P2.2/P2.3 ported only the
  `sh:maxInclusive 1.0` arm (`confidence > 1.0`), while pyshacl enforces BOTH
  `sh:minInclusive 0.0` and `sh:maxInclusive 1.0`. A `confidence < 0.0` claim was
  therefore rdflib-non-conforming but Cozo-conforming — opposite verdicts. The
  floor arm is now ported as `confidence-range-low.edn` (`:filter [[< ?conf 0.0]]`,
  SAME `:message`/`:path` as the ceiling arm), added to `ACTIVE_CONSTRAINTS` right
  after `confidence-range`. Both engines now flag a below-zero confidence on the
  `#confidence` path
  (`tests/test_constraint_ports.py::test_both_engines_flag_confidence_below_zero`).
  Because both confidence constraints share one `:message`, the path-keyed
  message-remap stays unambiguous. The C0.2 violating golden is unchanged in
  count (still 4 — the floor arm clears the existing rows); only the confidence
  violation's message becomes the range form `Claim confidence must be in
  [0.0, 1.0].`. The normalizer is now an explicitly audited raw→canonical
  transform: `shacl_report_violating_raw.json` freezes the pre-port pyshacl output
  and `test_normalizer_maps_raw_pyshacl_to_canonical` asserts
  `normalize(raw) == canonical` (de-circularizes the I-1 parity proof).

- **REQ-KG-012 / REQ-KG-013 are PARTIAL for `chapter-cites-verified`.** That shape
  compiles, executes, and is in `ACTIVE_CONSTRAINTS` under both engines, but it has
  **no production data path**: `project_ledger` loads `:chapter-section` EMPTY (no
  projector sources chapter→claim citation data from a real workspace). On a real
  workspace it is a guaranteed no-op; it fires only on hand-loaded test rows. The
  parity proof for this shape therefore rests on synthetic store rows, not a
  projected workspace, until a real `chapter-section` projector exists (future
  task). See `assets/kg-constraints/_DEFERRED.md`. The other constraints
  (status-enum, both confidence arms, text-cardinality, source-span-present,
  verified-derives) ARE exercised through the real projection path and remain
  FULLY ported.
