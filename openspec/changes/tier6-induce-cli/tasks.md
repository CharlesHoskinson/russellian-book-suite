# Tasks: tier6-induce-cli

See `docs/plans/2026-05-19-tier6-theory-induction.md` Phase
AA for full TDD steps. Task numbers correspond 1:1.

## Phase AA.1 — Subcommand registration

- [ ] AA1.1: Add three new `@cli.command` entries to
  `skills/neurosym-forge/scripts/forge_cli.py`: `induce`,
  `revise`, `theory`. Each wraps its body in the existing
  `@_handle` decorator. (REQ-AUTHOR-050)
- [ ] AA1.2: `forge --help` lists the new subcommands;
  `forge induce --help`, `forge revise --help`, and
  `forge theory --help` each render non-trivial help text.
  (REQ-AUTHOR-050)

## Phase AA.2 — `forge induce`

- [ ] AA2.1: Argument parser: `<project>` argument (defaults
  to walking up from cwd for the verifier root); `--folds N`
  (default 5); `--budget-usd N` (no default); `--dry-run`
  flag. (REQ-AUTHOR-051, REQ-AUTHOR-056)
- [ ] AA2.2: Shell out to `nbb scripts/induce_theory.cljs`
  with project path + folds + budget; capture stdout +
  stderr; propagate non-zero exit through
  `InductionPipelineError`. (REQ-AUTHOR-051)
- [ ] AA2.3: One-screen summary: total rules induced, total
  cost USD, top-3 highest-entrenchment rules with rule-id +
  entrenchment + support-doc-count. (REQ-AUTHOR-051)
- [ ] AA2.4: When `_semantic_index` is absent, print the
  warning per design.md "Semantic-index degraded mode" and
  proceed. (REQ-AUTHOR-054)
- [ ] AA2.5: `--dry-run` short-circuits before any file
  write; all stdout output still appears. (REQ-AUTHOR-056)

## Phase AA.3 — `forge revise`

- [ ] AA3.1: Argument parser: `<project>` argument;
  `--retracted-paper <id>` (repeatable);
  `--contradicting-atom <id>` (repeatable); `--dry-run`
  flag. At least one of `--retracted-paper` /
  `--contradicting-atom` must be passed (callback enforces).
  (REQ-AUTHOR-052, REQ-AUTHOR-056)
- [ ] AA3.2: Load `induced-theory.edn` and the sidecar;
  call `_agm_revision.revise_theory(...)`; render the
  `RevisionReport` per design.md "forge revise" output
  block. (REQ-AUTHOR-052)
- [ ] AA3.3: Prepend full-quarantine warning banner when
  `RevisionReport.full_quarantine_warning` is True.
  (REQ-AUTHOR-052)
- [ ] AA3.4: `--dry-run` runs the revision in memory but
  does not write the sidecar back. (REQ-AUTHOR-056)

## Phase AA.4 — `forge theory`

- [ ] AA4.1: Argument parser: `<project>` argument;
  `--rule <id>` flag for deep-dive. (REQ-AUTHOR-053)
- [ ] AA4.2: Aggregate output: rule count, status
  distribution, average entrenchment, total cost USD, top-5
  most-cited source documents. (REQ-AUTHOR-053)
- [ ] AA4.3: `--rule <id>` deep-dive: render every
  `:prov/*` field on the named rule per design.md "Rule
  deep-dive" output block. (REQ-AUTHOR-053)
- [ ] AA4.4: Graceful-degrade when the sidecar is missing or
  malformed (REQ-PROV-044 surface): print the structured
  error, continue with empty provenance, still render the
  rule list from `induced-theory.edn`. (REQ-AUTHOR-053)

## Phase AA.5 — Error-table extensions

- [ ] AA5.1: Extend `_cli_errors.interpret` with entries
  for `ProvenanceSidecarError`, `RevisionInputError`, and
  `InductionPipelineError`; each entry follows the
  `ERROR: ... / What likely happened: ... / Likely fix: ... /
  Reference: ...` four-line format from Phase U.

## Phase AA.6 — Tests

- [ ] AA6.1: `tests/test_forge_cli.py::test_induce_happy_path`
  — fixture verifier project, stub nbb invocation, assert
  summary printed + sidecar populated. (REQ-AUTHOR-055)
- [ ] AA6.2: `tests/test_forge_cli.py::test_induce_dry_run_writes_no_files`
  — `--dry-run` path; assert stdout populated and files
  unchanged. (REQ-AUTHOR-055, REQ-AUTHOR-056)
- [ ] AA6.3: `tests/test_forge_cli.py::test_induce_warns_when_semantic_index_absent`
  — fixture without a built index; assert warning printed.
  (REQ-AUTHOR-054)
- [ ] AA6.4: `tests/test_forge_cli.py::test_revise_happy_path`
  — fixture sidecar; `--retracted-paper pmid:fixture`;
  assert `RevisionReport` rendered. (REQ-AUTHOR-055)
- [ ] AA6.5: `tests/test_forge_cli.py::test_revise_requires_at_least_one_input`
  — neither flag passed; assert `RevisionInputError`
  rendered. (REQ-AUTHOR-055)
- [ ] AA6.6: `tests/test_forge_cli.py::test_theory_aggregate_and_deep_dive`
  — fixture sidecar; both `forge theory` and `forge theory
  --rule <id>` paths exercised. (REQ-AUTHOR-055)

## Phase AA.7 — Commit

- [ ] AA7.1: Commit the three subcommands + error-table
  extensions + tests together once AA1-AA6 are green.
