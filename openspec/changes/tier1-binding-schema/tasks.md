# Tasks: tier1-binding-schema

See `docs/plans/2026-05-18-tier1-general-purpose.md` Phase C for full
TDD steps. Task numbers correspond 1:1.

## Phase C.1 — Golden test files

- [ ] C1.1: Create `skills/neurosym-forge/tests/golden/canonical_var_name.edn` with 8-10 algorithm vectors covering `:foo`, `":foo"`, `"?foo"`, `Bermuda`, etc. (REQ-EDN-040)
- [ ] C1.2: Create `tests/golden/expression_atom.edn`, `opaque_atom.edn`, `context_atom.edn`, `predicate_entry.edn`, `verdict.edn`, `constraint_entry.edn`. (REQ-EDN-041)
- [ ] C1.3: Commit the goldens.

## Phase C.2 — Python canonical_var_name + round-trip test

- [ ] C2.1: Add failing test `skills/neurosym-forge/tests/test_canonical_var_name.py::test_python_matches_golden`. (REQ-EDN-042)
- [ ] C2.2: Add `canonical_var_name(pred: str, subj: str) -> str` to `skills/neurosym-forge/scripts/_canonical.py`. (REQ-EDN-042)
- [ ] C2.3: Update callers in `_codegen_axioms_lib.py` and `ingest_ledger.py` to use the canonical function. (REQ-EDN-043)
- [ ] C2.4: Test passes.
- [ ] C2.5: Add `tests/test_golden_round_trip.py::test_python_byte_identical_round_trip` parametrised over the 6 atom-shape goldens. (REQ-EDN-044)
- [ ] C2.6: Commit.

## Phase C.3 — CLJS canonical-var-name

- [ ] C3.1: Add a failing test in `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/test/__project__/booklogic_test.cljs.tmpl` (one that loads the golden file and asserts each row's :want matches the function output). Document the failure mode. (REQ-EDN-045)
- [ ] C3.2: Add `canonical-var-name` function to `booklogic.cljs.tmpl`. (REQ-EDN-045)
- [ ] C3.3: Replace inline `(str (name pred) "_" (name subj))` constructions with calls to `canonical-var-name`.
- [ ] C3.4: Commit.

## Phase C.4 — Rust canonical_var_name

- [ ] C4.1: Add failing integration test `verifiers/osmotic_pressure/rust-verifier/tests/canonical_var_name.rs` that reads the golden EDN and asserts the function output. (REQ-EDN-046)
- [ ] C4.2: Add `pub fn canonical_var_name(predicate: &str, subject: &str) -> String` to a new `verifiers/osmotic_pressure/rust-verifier/src/canonical.rs`. (REQ-EDN-046)
- [ ] C4.3: Update `smt.rs` to call `canonical::canonical_var_name(...)` instead of inline `format!`. (REQ-EDN-047)
- [ ] C4.4: Run unit tests — confirm clean + doctored still pass.
- [ ] C4.5: Add Rust integration test that parses each golden file and asserts expected `Edn::*` variants. (REQ-EDN-048)
- [ ] C4.6: Mirror the canonical.rs + golden integration to bermuda.
- [ ] C4.7: Commit.

## Phase C.5 — Stop-gap 1: keyword emission in ingest_ledger

- [ ] C5.1: Failing test `test_ingest_emits_keywords_not_strings` that asserts the emitted EDN parses with `Edn::Key` (not `Edn::Str`) for :predicate and :subject. (REQ-EDN-049)
- [ ] C5.2: Modify `verifiers/osmotic_pressure/scripts/ingest_ledger.py` to emit `Keyword` objects. (REQ-EDN-049)
- [ ] C5.3: Update `smt.rs` to drop the `Edn::Str(s) => s.clone()` fallback (no longer needed).
- [ ] C5.4: Run smoke — verify still passes.
- [ ] C5.5: Commit.

## Phase C.6 — Stop-gap 2: float emission without scientific notation

- [ ] C6.1: Failing test `test_emit_float_never_uses_scientific_notation` over a range of values from 1e-20 to 1e20. (REQ-EDN-050)
- [ ] C6.2: Replace `repr(f)` in `_edn_writer.py:_emit_float` with the fixed-point fallback. (REQ-EDN-050)
- [ ] C6.3: Commit.

## Phase C.7 — Stop-gap 3: EdnList vs EdnVector

- [ ] C7.1: Failing test `test_list_paren_round_trip` that asserts `(a b c)` round-trips through reader+writer as `(a b c)`, not `[a b c]`. (REQ-EDN-051)
- [ ] C7.2: Introduce `EdnList` and `EdnVector` dataclasses in `_edn_reader.py`; reader emits the discriminated form. (REQ-EDN-051)
- [ ] C7.3: Update `_edn_writer.py` to emit `(...)` for `EdnList`, `[...]` for `EdnVector`. (REQ-EDN-051)
- [ ] C7.4: Audit callers of `_edn_reader` for `isinstance(x, list)` checks — switch to `isinstance(x, (EdnList, EdnVector))` where the bare-list semantics is intentional. (REQ-EDN-051)
- [ ] C7.5: Commit.

## Phase C.8 — Schema-file generation

- [ ] C8.1: Failing test that loads `verifiers/osmotic_pressure/rules/booklogic-schema.edn` after `nbb booklogic .` and asserts the four predicates are present with `:return :real`. (REQ-EDN-052)
- [ ] C8.2: Update `booklogic.cljs.tmpl emit-schema-edn` (new function) to write the schema file. (REQ-EDN-052)
- [ ] C8.3: Add Python schema validator: `ingest_ledger.py` reads the schema and rejects unknown predicate names. (REQ-EDN-053)
- [ ] C8.4: Commit.

## Phase C.9 — Open PR

- [ ] C9.1: Push branch `feat/tier1-binding-schema` and open PR.
- [ ] C9.2: Merge on green CI.
