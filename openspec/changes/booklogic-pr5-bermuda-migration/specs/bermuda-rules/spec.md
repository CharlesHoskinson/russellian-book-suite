# Capability delta: bermuda-rules — change: booklogic-pr5-bermuda-migration

## ADD

### REQ-BERMUDA-RULES-010 — Ubiquitous

`verifiers/bermuda/rules/sorts.edn` shall declare the sort registry:
`:entity`, `:claim`, `:source`, `:span`, `:formula`, `:verdict`, plus
primitives.

**Rationale:** Bermuda's BookLogic source needs an explicit sort universe.
**Tested by:** `verifiers/bermuda/tests/test_booklogic_source_shape.py::test_sorts_complete` (added in pr5 T1.1)

### REQ-BERMUDA-RULES-011 — Ubiquitous

`verifiers/bermuda/rules/predicates.edn` shall declare all five existing
predicates (`parishes-count`, `named-islands-count`, `currency-pegged-at-parity`,
`airport-on-island`, `cedar-binomial`) with the typings present in the
pre-migration `prose_patterns.py`.

**Rationale:** Migration must preserve current semantics.
**Tested by:** `test_booklogic_source_shape.py::test_existing_predicates_preserved` (added in pr5 T1.2)

### REQ-BERMUDA-RULES-012 — Ubiquitous

`verifiers/bermuda/rules/predicates.edn` shall additionally declare four new
quantitative predicates: `population` (`:int`), `land-area-km2` (`:real`),
`gdp-usd-billion` (`:real`), `hospital-beds-kemh` (`:int`).

**Rationale:** Mission D4 promises these new claims.
**Tested by:** `test_booklogic_source_shape.py::test_quantitative_predicates_added` (added in pr5 T1.2)

### REQ-BERMUDA-RULES-013 — Ubiquitous

`verifiers/bermuda/rules/lifts.edn` shall contain one `deflift` for every
regex pattern previously hand-coded in `verifiers/bermuda/scripts/prose_patterns.py`,
plus four new lifts for the quantitative predicates.

**Rationale:** Single source of truth for prose-extraction patterns.
**Tested by:** `test_booklogic_source_shape.py::test_lifts_cover_existing_regexes` (added in pr5 T1.3)

### REQ-BERMUDA-RULES-014 — Ubiquitous

`verifiers/bermuda/rules/rules.edn` shall preserve every R-rule's semantics
from any pre-migration `rules/rules.edn` (if such file existed) or remain
empty if no such rules were present pre-migration.

**Rationale:** Migration is semantically faithful.
**Tested by:** `test_booklogic_source_shape.py::test_rules_preserved_or_empty` (added in pr5 T1.4)

### REQ-BERMUDA-RULES-015 — Ubiquitous

`verifiers/bermuda/rules/constraints.edn` shall declare one `defconstraint`
per fact previously asserted by `canonical.rs` (parishes=9, named-islands=181,
currency-peg=true, airport-on-island=:St_Davids_Island, cedar-binomial="Juniperus
bermudiana").

**Rationale:** Constraints replace the hand-coded canonical-fact axioms.
**Tested by:** `test_booklogic_source_shape.py::test_canonical_facts_carried_over` (added in pr5 T1.5)

### REQ-BERMUDA-RULES-016 — Ubiquitous

`verifiers/bermuda/rules/constraints.edn` shall additionally declare
one `defconstraint` per quantitative predicate asserting the canonical
value (e.g. `population` ≈ 64,000) with appropriate tolerance.

**Rationale:** Quantitative predicates need anchor values.
**Tested by:** `test_booklogic_source_shape.py::test_quantitative_constraints_added` (added in pr5 T1.5)

### REQ-BERMUDA-RULES-017 — Ubiquitous

`verifiers/bermuda/rules/queries.edn` shall declare at least one Cozo
`defquery` exercising the data-path verification (e.g. "find every
load-bearing claim with posterior < 0.80").

**Rationale:** Bermuda is the first Cozo consumer in production.
**Tested by:** `test_booklogic_source_shape.py::test_at_least_one_query` (added in pr5 T1.6)

### REQ-BERMUDA-RULES-018 — Ubiquitous

`verifiers/bermuda/rules/remedies.edn` shall declare at least one
`defremedy` (e.g. "if unsat-core surfaces a claim, propose `:refuted`
with `:requires :human-review`").

**Rationale:** First production remedy.
**Tested by:** `test_booklogic_source_shape.py::test_at_least_one_remedy` (added in pr5 T1.7)

### REQ-BERMUDA-RULES-019 — Ubiquitous

`verifiers/bermuda/rust-verifier/src/canonical.rs` shall not exist after
PR-5.

**Rationale:** Codegen makes the hand-coded file obsolete.
**Tested by:** `test_booklogic_source_shape.py::test_canonical_rs_deleted` (added in pr5 T2.3)

### REQ-BERMUDA-RULES-020 — Ubiquitous

`verifiers/bermuda/scripts/prose_patterns.py` shall, after PR-5, contain
no regex patterns; it shall load all patterns from the lift-generated
table at `verifiers/bermuda/rules/.compiled/lift_patterns.py` (or
equivalent path written by the BookLogic compiler).

**Rationale:** Pattern data lives in `lifts.edn`; the Python module is a
thin loader.
**Tested by:** `verifiers/bermuda/tests/test_prose_patterns_is_loader.py::test_no_inline_regexes` (added in pr5 T2.4)

### REQ-BERMUDA-RULES-021 — State-driven

While `examples/bermuda-manual/claims/ledger.jsonl` is current, the ledger
shall contain at least one verified claim per quantitative predicate
(`population`, `land-area-km2`, `gdp-usd-billion`, `hospital-beds-kemh`).

**Rationale:** End-to-end verification requires data to verify.
**Tested by:** `test_booklogic_source_shape.py::test_ledger_carries_quantitative_claims` (added in pr5 T3.1)

## MODIFY

(none — bermuda-rules has only ADD deltas across the v0.4 sprints; the
seed.edn / grounded.edn syntax migration is captured under REQ-EDN-010
and REQ-EDN-011)

## REMOVE

(none)
