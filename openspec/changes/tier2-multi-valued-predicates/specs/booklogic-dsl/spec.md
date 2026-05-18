# Capability delta: booklogic-dsl — change: tier2-multi-valued-predicates

> **REQ-ID note:** Original Tier 2 plan called for REQ-DSL-040..045,
> but `booklogic-pr4-active-forms` already claims REQ-DSL-040 in its
> unmerged change folder. This delta uses REQ-DSL-050..055 to keep
> IDs globally unique. Contents match the original plan.

## ADD

### REQ-DSL-050 — Ubiquitous

`defpredicate` SHALL accept a multi-valued return shape of the form
`[:vector <sort-keyword>]` or `[:set <sort-keyword>]` in the
return-sort position, in addition to the existing scalar sort. The
inner `<sort-keyword>` SHALL be either a base sort (`:int`, `:real`,
`:bool`, `:string`) or a Keyword previously declared via `defsort`.
Nested containers (`[:vector [:set ...]]`) are NOT in scope for this
change.

**Rationale:** Multi-valued observables ("set of supporting chapters",
"list of declared species", "vector of edge weights") are the
framework's next class of constraint. Surface syntax for declaring
them must come before any encoder work.
**Tested by:** `skills/neurosym-forge/tests/test_defpredicate_grammar.py::test_vector_return_sort_accepted` (added in E3.1.1) and `::test_set_return_sort_accepted` (added in E3.1.3)

### REQ-DSL-051 — Ubiquitous

When a `defpredicate` declares `:return [:vector <sort>]`, the codegen
SHALL lower applications of that predicate to a Z3 `Array<Int, <sort>>`
symbol whose name follows REQ-EDN-042 canonical naming, plus a paired
`Int::new_const("<var-name>_len")` symbol holding the vector length.

**Rationale:** Z3 `Array<Int, T>` plus a length witness gives the
aggregate operators (`sum`, `count`, `forall...in`) constant-time
encodings while keeping every call inside the typed z3-rs Rust API
(see design.md "Why Z3 Array, not Z3 Sequence?").
**Tested by:** `skills/neurosym-forge/scripts/tests/test_codegen_axioms_collections.py::test_vector_predicate_lowers_to_array` (added in E3.2.1)

### REQ-DSL-052 — Ubiquitous

When a `defpredicate` declares `:return [:set <sort>]`, the codegen
SHALL lower applications of that predicate to a Z3 `Set<<sort>>` symbol
via the standard z3-rs set-theory API, whose name follows REQ-EDN-042
canonical naming.

**Rationale:** Sets capture unordered, membership-testing observables
("the set of upstream chapters"); the standard Z3 set theory is the
direct lowering target with first-class z3-rs support.
**Tested by:** `test_codegen_axioms_collections.py::test_set_predicate_lowers_to_z3_set` (added in E3.2.3)

### REQ-DSL-053 — Optional feature

WHERE a `defconstraint :assert` form uses one of the aggregate
operators `(sum vec)`, `(count vec)`, `(in elem set)`, or
`(forall ?x in coll body)`, the codegen SHALL desugar the operator to
the equivalent Z3 form:
- `sum`  → `Real::add` / `Int::add` fold over the array slice `[0, len)`
- `count` → the paired `<var>_len` `Int` symbol
- `in` → `Set::member`
- `forall ?x in coll body` → bounded `Bool::and` over the array slice for
  vector `coll`; quantified Z3 `forall` over the set sort for set `coll`.

**Rationale:** Without aggregate operators, multi-valued return-sorts
exist but cannot be used in constraints. The operator set above
covers the three motivating examples (set of supporting chapters,
list of species, vector of edge weights) in one round-trip.
**Tested by:** `test_codegen_axioms_collections.py::test_sum_aggregate_emits_array_fold` (added in E3.3.1) and three sibling tests for `count`, `in`, `forall`.

### REQ-DSL-054 — Unwanted behaviour

IF an atom emitted by ingest binds a scalar value to a predicate whose
schema entry declares a multi-valued return shape (`[:vector ...]` or
`[:set ...]`), THEN `smt::check_all` SHALL fail with an `Error::Smt`
whose message:
1. names the predicate,
2. names the declared return shape, and
3. names the actual value shape received (e.g., "expected `[:set :chapter]`,
   got scalar `Int(42)`").

**Rationale:** The asymmetric case — declaring a set but emitting a
scalar — is the multi-valued analogue of the predicate-typo bug
REQ-EDN-053 catches. Failing at `check_all` keeps the silent-OPAQUE
class of bug closed for multi-valued predicates too.
**Tested by:** `verifiers/osmotic_pressure/rust-verifier/tests/multi_valued_binding.rs::scalar_value_for_set_predicate_errors` (added in E3.4.1)

### REQ-DSL-055 — Ubiquitous

The generated schema file `rules/booklogic-schema.edn` (REQ-EDN-052)
SHALL encode multi-valued return shapes in the same `[:vector <sort>]`
/ `[:set <sort>]` surface form they were declared in; the Python
schema reader in `ingest_ledger.py` SHALL parse the new shape and
make it available to the atom emitter so multi-valued atoms carry the
declared shape through to the Rust verifier.

**Rationale:** Single source of truth for predicate signatures across
the three languages (the same principle that drove REQ-EDN-052). The
schema file is the read-once contract; everything downstream consults
it.
**Tested by:** `verifiers/osmotic_pressure/tests/test_schema_file.py::test_schema_emits_vector_set_return_shapes` (added in E3.5.1)
