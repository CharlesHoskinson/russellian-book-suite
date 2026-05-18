# Capability delta: datalog — change: tier3-cozo-runtime

This change introduces a new capability `datalog`, the
framework's Cozo-backed Datalog surface. Today `defquery` is
wired-builder, `defconstraint :backend :cozo` is DROP, and
`defremedy` is external per `SUPPORT_MATRIX.md`. After this
change all three flip to wired (`defremedy` for the
query-bound subset).

## ADD

### REQ-DATALOG-040 — Ubiquitous

At `make ci` time, the framework SHALL invoke the Cozo runtime
on every `defquery` declared in `rules/queries.edn` via
`kg::ingest_and_summarize(&claims)`, and SHALL persist the
result to `work/query-results.edn` in a top-level map of the
shape `{:queries {Q-ID [row...]}}`. Queries returning zero rows
SHALL still appear with an empty vector so consumers can
distinguish "ran-empty" from "not-registered".

**Rationale:** Today `codegen_kg.py` emits a valid `kg.rs` but
the verifier's `main.rs` never calls into it during smoke. The
result is invisible to authors and to `book-qa`.
**Tested by:** `verifiers/osmotic_pressure/rust-verifier/tests/datalog_smoke.rs::query_results_edn_written_after_make_ci` (added in H1.2)

### REQ-DATALOG-041 — Optional feature

WHERE a `defconstraint` form declares `:backend :cozo`, the
framework SHALL evaluate the constraint via Cozo Datalog
clauses emitted into a generated `cozo_constraints.rs`
module, and SHALL merge its sat/unsat verdict with Z3's. The
combined `:status` field of the verdict SHALL be the worst-case
of Z3's status and Cozo's status (e.g. `:unsat` if either is
`:unsat`).

**Rationale:** Retires the silent DROP at
`codegen_axioms.py:139` for `:cozo`-backed constraints; lets
authors write Datalog constraints that actually gate the
verdict.
**Tested by:** `tests/datalog_backend.rs::cozo_backed_constraint_affects_status` (added in H2.3)

### REQ-DATALOG-042 — Ubiquitous

The combined verdict format SHALL add a `:queries [...]` field
listing all query names that returned at least one row. The
field SHALL be a vector of Keywords matching the `defquery`
IDs; ordering SHALL be deterministic (lexicographic by ID).

**Rationale:** Gives downstream consumers (`book-qa`, the QA
gate, the dashboard) a stable handle on which queries fired
without forcing them to re-read `work/query-results.edn`.
**Tested by:** `tests/datalog_verdict.rs::queries_field_lists_only_non_empty_query_ids` (added in H3.1)

### REQ-DATALOG-043 — Optional feature

WHERE a `defremedy` form's `:when` clause references a
`defquery` name (e.g. `:when {:query :Q002-low-confidence}`),
the framework SHALL bind the query's result rows into the
remedy's `:propose` action surface by materialising
`:remedy-bindings <remedy-id> :rows` = `[<row-map>...]` in the
verdict. Remedies whose `:when` clause does NOT reference a
`defquery` SHALL be unaffected and continue to flow through the
existing external (book-qa) path.

**Rationale:** Lets `defremedy` consume Datalog query results
directly; this is the missing wiring that made `defremedy`
purely declarative before.
**Tested by:** `tests/datalog_remedy.rs::query_bound_remedy_carries_rows_in_verdict` (added in H3.2)

### REQ-DATALOG-044 — Unwanted behaviour

IF a Cozo query takes longer than `VERIFIER_DATALOG_TIMEOUT_MS`
(default 10000), THEN the framework SHALL terminate that
query's evaluation, SHALL surface a structured warning of the
shape `{:phase :datalog :reason :datalog-timeout :query
:Q###-... :elapsed-ms <int>}` on the verdict's `:warnings`
list, and SHALL continue evaluating the remaining queries. The
timed-out query SHALL NOT block other queries' results from
reaching the verdict.

**Rationale:** Cozo can run unbounded scripts; without a
timeout one pathological query stalls every `make ci`.
**Tested by:** `tests/datalog_timeout.rs::slow_query_emits_timeout_warning_and_does_not_block` (added in H4.2)

### REQ-DATALOG-045 — Ubiquitous

`skills/neurosym-forge/SUPPORT_MATRIX.md` SHALL be updated as
part of this change so that:

- the `defquery` row's Status flips from `wired-builder` to
  `wired`,
- the `defconstraint :backend :cozo` row's Status flips from
  `DROP` to `wired`,
- the `defremedy` row gains an explicit `wired (query-bound)`
  marker for remedies whose `:when` references a `defquery`,
- the `wired-builder` legend entry is retired,
- the `external` legend entry shrinks to "remedies whose
  `:when` clause does not reference a `defquery`".

The drift-lint `tests/test_support_matrix.py` SHALL pass
against the updated matrix once `kg::ingest_and_summarize` is
called from `main.rs` and the verdict carries `:queries` /
`:cozo-defects` / `:remedy-bindings` fields.

**Rationale:** Without the matrix update, the framework
documents a stub status for code that is now live; the lint
catches the drift.
**Tested by:** `tests/test_support_matrix.py::test_matrix_matches_codegen_after_cozo_promotion` (added in H5.1)
