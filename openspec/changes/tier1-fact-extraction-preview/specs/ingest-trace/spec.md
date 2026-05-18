# Capability delta: ingest-trace — change: tier1-fact-extraction-preview

## ADD

### REQ-INGEST-040 — Ubiquitous

The framework SHALL provide a `scripts/extract_preview.py` tool that
accepts `--claims <jsonl>` and `--predicates <edn>` and prints a
per-predicate fact-count summary to stdout including: predicate name,
number of `:expression` atoms emitted, and one sample value per
predicate.

**Rationale:** Authors need a one-screen view of what ingest actually
extracts before invoking the verifier, so silent-OPAQUE-fallthrough
regex bugs surface at the ingest layer rather than as spurious `:sat`
verdicts at the SMT layer.
**Tested by:** `verifiers/osmotic_pressure/scripts/tests/test_extract_preview.py::test_summary_includes_per_predicate_counts` (added in A1.1)

### REQ-INGEST-041 — Unwanted behaviour

IF the fraction of input claims emitted as `:OPAQUE` (kind = `:symbol`
with name = `:OPAQUE`) exceeds a configurable threshold (default 0.50)
THEN extract_preview.py SHALL exit with non-zero status and print a
prominent error message naming the offending fraction.

**Rationale:** A high OPAQUE fraction almost always means a lift regex
is broken (wrong dialect, typo, or apostrophe handling). Failing the
gate makes the silent class of bug structurally impossible to merge.
**Tested by:** `test_extract_preview.py::test_threshold_exit_on_high_opaque` (added in A1.4)

### REQ-INGEST-042 — Optional feature

WHERE the `--dry-run` flag is passed, extract_preview.py SHALL print
the EDN that would have been written to `work/claims.edn` without
touching the filesystem.

**Rationale:** Lets authors iterate on regex tuning without polluting
the working tree.
**Tested by:** `test_extract_preview.py::test_dry_run_does_not_write_file` (added in A1.5)

### REQ-INGEST-043 — Ubiquitous

The extract_preview.py output SHALL include a single-line JSON tail
of the form `JSON: {"opaque": N, "total": M, "by_predicate": {...}}`
on stdout, so the report is machine-readable.

**Rationale:** Enables CI logging, dashboards, and historical trend
tracking without parsing the human-readable table.
**Tested by:** `test_extract_preview.py::test_json_tail_parseable` (added in A1.6)

### REQ-INGEST-044 — Ubiquitous

Each verifier project's `Makefile` SHALL define an `extract` target
that runs `python scripts/extract_preview.py` against the project's
primary fixture (typically `fixtures/claims_clean.jsonl`).

**Rationale:** Per-project Make integration so authors can run
`make extract` locally without remembering the script path.
**Tested by:** `verifiers/osmotic_pressure/tests/test_makefile_targets.py::test_extract_target_exists` (added in A2.1)

### REQ-INGEST-045 — Event-driven

WHEN `make ci` is invoked the framework SHALL run the `extract` target
between `build` and `smoke`, causing CI to fail at the extract gate
(per REQ-INGEST-041) rather than producing a spurious `:sat` later in
the smoke pytest.

**Rationale:** Makes the gate a CI requirement, not an opt-in tool.
**Tested by:** Regression suite in REQ-INGEST-048.

### REQ-INGEST-046 — Ubiquitous

The neurosym-forge scaffold template's `Makefile.tmpl` SHALL render an
`extract` target into every new project, identical in semantics to
REQ-INGEST-044.

**Rationale:** Every future verifier inherits the gate by default.
**Tested by:** `skills/neurosym-forge/tests/test_scaffold_bake.py::test_baked_makefile_has_extract_target` (added in A3.1)

### REQ-INGEST-047 — Ubiquitous

The neurosym-forge scaffold SHALL vendor an `extract_preview.py` shim
into every new project's `scripts/` directory that imports from a
canonical library in the skill (mirroring the existing
`codegen_axioms.py`/`_codegen_axioms_lib.py` vendoring pattern).

**Rationale:** Avoids divergence between the skill's canonical preview
and per-project copies.
**Tested by:** `test_scaffold_bake.py::test_baked_extract_preview_imports_lib` (added in A3.2)

### REQ-INGEST-048 — Unwanted behaviour

IF a `deflift` regex in a baked project's `rules/booklogic/lifts.edn`
uses JS-style named groups `(?<v>...)` instead of Python-form
`(?P<v>...)`, THEN the project's `make ci` SHALL fail at the `extract`
step with the OPAQUE-fraction gate triggered, before reaching the
`smoke` step.

**Rationale:** Re-injects the sprint-5 silent-failure-by-regex bug and
asserts the new gate catches it.
**Tested by:** `skills/neurosym-forge/tests/regression/test_sprint5_bug_catches.py::test_bug7_js_named_group_caught_by_extract_gate` (added in A3.3; supersedes the existing test_bug7 that only checks the standalone regex compile script)
