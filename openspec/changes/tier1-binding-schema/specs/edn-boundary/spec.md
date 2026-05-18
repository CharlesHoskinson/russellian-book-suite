# Capability delta: edn-boundary — change: tier1-binding-schema

## ADD

### REQ-EDN-040 — Ubiquitous

The framework SHALL ship a golden test file
`skills/neurosym-forge/tests/golden/canonical_var_name.edn` that
enumerates at least 8 (predicate, subject, want) tuples covering the
identifier-form combinations:
- bare keyword `:foo`
- keyword-string `":foo"`
- query-prefixed symbol `"?foo"`
- dashed slug `vant-hoff-i`
- mixed-case entity name `Bermuda`

**Rationale:** The golden file is the canonical-name algorithm's
specification; all three language implementations must agree on it.
**Tested by:** existence check in `test_canonical_var_name.py::test_golden_present_and_well_formed` (added in C1.1)

### REQ-EDN-041 — Ubiquitous

The framework SHALL ship golden EDN test files at
`skills/neurosym-forge/tests/golden/{expression_atom, opaque_atom,
context_atom, predicate_entry, verdict, constraint_entry}.edn`,
representing the six round-trip-critical EDN shapes the framework
emits across the CLJS / Python / Rust boundary.

**Rationale:** Provides shared ground truth that all three layers must
parse and emit identically.
**Tested by:** `test_golden_round_trip.py::test_golden_files_exist_and_parse` (added in C1.2)

### REQ-EDN-042 — Ubiquitous

The Python `canonical_var_name(predicate, subject) -> str` function in
`skills/neurosym-forge/scripts/_canonical.py` SHALL produce the
expected `:want` string from `golden/canonical_var_name.edn` for every
golden row.

**Rationale:** One canonical algorithm, one source of truth, three
identical implementations.
**Tested by:** `test_canonical_var_name.py::test_python_matches_golden` (added in C2.1)

### REQ-EDN-043 — Ubiquitous

Every existing Python caller that constructs a Z3-variable-name string
(`_codegen_axioms_lib.py`, `ingest_ledger.py`) SHALL be refactored to
call `canonical_var_name(...)` rather than inline string concatenation.

**Rationale:** Eliminates the independent reconstructions that drift.
**Tested by:** Grep-based test `test_canonical_var_name.py::test_no_inline_var_name_construction` (added in C2.3)

### REQ-EDN-044 — Ubiquitous

Every golden EDN file at `tests/golden/*.edn` SHALL round-trip
byte-identically through `read_edn(write_edn(read_edn(content)))` in
Python.

**Rationale:** Asserts the Python EDN reader/writer is closed under
itself — a prerequisite for cross-language agreement.
**Tested by:** `test_golden_round_trip.py::test_python_byte_identical_round_trip` (added in C2.5)

### REQ-EDN-045 — Ubiquitous

The CLJS `booklogic.cljs.tmpl` SHALL define a `canonical-var-name`
function that produces the same string as the Python implementation
for every row in `golden/canonical_var_name.edn`.

**Rationale:** CLJS authors writing `defconstraint :assert` forms must
get the same variable name as the Python codegen.
**Tested by:** `booklogic_test.cljs.tmpl::canonical-var-name-matches-golden` (added in C3.1)

### REQ-EDN-046 — Ubiquitous

Each verifier's `rust-verifier/src/canonical.rs` SHALL expose a
`pub fn canonical_var_name(predicate: &str, subject: &str) -> String`
that produces the same string as the Python implementation for every
row in `golden/canonical_var_name.edn`.

**Rationale:** Rust runtime must agree with Python codegen and CLJS
compiler on variable names so the Z3 symbols match.
**Tested by:** `verifiers/osmotic_pressure/rust-verifier/tests/canonical_var_name.rs::matches_golden` (added in C4.1)

### REQ-EDN-047 — Ubiquitous

`smt::check_all` in every verifier SHALL call
`canonical::canonical_var_name(predicate, subject)` instead of inline
`format!`-based string assembly.

**Rationale:** Single call site means one place to update if the
naming algorithm ever changes.
**Tested by:** Grep-based assertion `test_canonical_var_name.py::test_rust_smt_uses_canonical_function` (added in C4.3)

### REQ-EDN-048 — Ubiquitous

The Rust integration test `verifiers/<verifier>/rust-verifier/tests/golden.rs`
SHALL parse every file in `skills/neurosym-forge/tests/golden/*.edn`
with edn-rs and assert that each field has the expected `Edn::*`
variant (e.g., `:kind` is `Edn::Key`, `:value` for a real-typed atom
is `Edn::Double`, never `Edn::Str`).

**Rationale:** Closes the cross-language type-asymmetry leak surface
(keyword-vs-string, int-vs-double, list-vs-vector).
**Tested by:** `tests/golden.rs::all_golden_files_parse_with_expected_variants` (added in C4.5)

### REQ-EDN-049 — Ubiquitous

The Python `ingest_ledger.py` SHALL emit `Keyword` objects (which
`_edn_writer` serialises as `:foo`) for the `:predicate` and `:subject`
fields of every emitted atom, not f-string-formatted colon-prefixed
strings.

**Rationale:** A keyword written as a string is a keyword silently
demoted to a string; the existing Rust shim accepting both `Edn::Key`
and `Edn::Str` is a migration artefact that we now retire.
**Tested by:** `test_ingest_keyword_emission.py::test_emits_keywords_not_strings` (added in C5.1)

### REQ-EDN-050 — Unwanted behaviour

IF a float value `f` is written via `_edn_writer.py`, THEN the
emitted token SHALL NOT contain the character `e` or `E` (no
scientific notation), for any finite `f` in the f64 range.

**Rationale:** `edn-rs 0.19` does not parse scientific notation;
emitting it silently falls back to `Edn::Str` on the Rust side and
the SMT axiom assertion silently uses a String variable instead of
a Real.
**Tested by:** `test_emit_float_never_uses_scientific_notation` (added in C6.1) covering 1e-20, 6.022e23, etc.

### REQ-EDN-051 — Ubiquitous

The Python `_edn_reader.py` SHALL distinguish EDN list `(...)` from
vector `[...]` by returning `EdnList` and `EdnVector` dataclasses
respectively, and `_edn_writer.py` SHALL emit the matching delimiter
form for each.

**Rationale:** CLJS pattern-matching code (meander dispatch on
`(list? form)`) breaks silently when Python erases the distinction on
round-trip.
**Tested by:** `test_list_vs_vector.py::test_paren_round_trip_preserved` (added in C7.1)

### REQ-EDN-052 — Ubiquitous

The CLJS `booklogic.cljs.tmpl` SHALL emit a generated schema file
`rules/booklogic-schema.edn` containing every declared sort and every
declared predicate with `:arg-sorts` and `:return`, derived from the
`defsort` and `defpredicate` forms in `rules/booklogic/*.edn`.

**Rationale:** Single source of truth for the framework's type signature
across the three languages.
**Tested by:** `verifiers/osmotic_pressure/tests/test_schema_file.py::test_schema_lists_four_predicates_with_return_real` (added in C8.1)

### REQ-EDN-053 — Unwanted behaviour

IF `ingest_ledger.py` encounters a predicate name not present in
`rules/booklogic-schema.edn`, THEN it SHALL exit non-zero with an
error naming the unknown predicate, before emitting any atom.

**Rationale:** A typo in a predicate name (`:Osmotic-Pressure` vs
`:osmotic-pressure-pa`) currently silently emits zero atoms; the
schema validator turns this into a loud failure.
**Tested by:** `test_ingest_unknown_predicate.py::test_typo_predicate_rejected` (added in C8.3)
