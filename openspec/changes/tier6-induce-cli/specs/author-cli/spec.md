# Capability delta: author-cli — change: tier6-induce-cli

Phase U (`tier5-author-cli`) established the `forge`
binary with REQ-AUTHOR-040..046 covering `add-constraint`,
`suggest-lifts`, `explain-defect`, `similar`, and `render`.
This change extends the same capability with
REQ-AUTHOR-050..056, adding three subcommands —
`induce`, `revise`, and `theory` — that surface the
Tier 6 inducer, the AGM revision algorithm, and the
provenance sidecar to authors.

## ADD

### REQ-AUTHOR-050 — Ubiquitous

`skills/neurosym-forge/scripts/forge_cli.py` SHALL gain
three new click subcommands on the existing `cli` group:
`induce`, `revise`, and `theory`. Each subcommand SHALL
wrap its body in the existing `_handle` error decorator from
REQ-AUTHOR-045 so framework errors render through the
`_cli_errors.interpret` table without raw stack traces. The
`forge --help` output SHALL list the three new subcommands
alongside the Phase U subcommands; each subcommand's
`--help` SHALL render non-trivial argument and flag
documentation.

**Rationale:** Reusing the Phase U decorator + error-table
pattern keeps the user-visible failure surface uniform across
Tier 5 and Tier 6 subcommands; listing in `--help` is the
discoverability gate authors hit before they read any docs.
**Tested by:**
`tests/test_forge_cli.py::test_induce_revise_theory_subcommands_exposed`
(added in AA1.1-AA1.2)

### REQ-AUTHOR-051 — Optional feature

WHERE the user runs `forge induce <project> [--folds N]
[--budget-usd N] [--dry-run]`, the CLI SHALL: (a) shell out
to the nbb orchestrator at `scripts/induce_theory.cljs`
with the project path, folds value (default `5`), and
optional budget; (b) on a successful orchestrator exit, emit
`rules/booklogic/induced-theory.edn` and
`rules/booklogic/induced-theory.prov.edn` per the Phase Y
schema; (c) print a one-screen summary listing total rules
induced, total cost USD, and the top-3 highest-entrenchment
rules with their rule-id, entrenchment value, and
support-doc-count. The `--folds` default SHALL be `5`; the
`--budget-usd` flag SHALL have no default (opt-in).

**Rationale:** A single command from the author's
perspective hides the four-stage pipeline (grammar enforcer +
candidate generator + SMT fitter + provenance writer) behind
one user surface; the top-3 summary gives the author a
"what's the best of what we found?" signal before they
inspect the full sidecar via `forge theory`.
**Tested by:**
`tests/test_forge_cli.py::test_induce_happy_path`,
`tests/test_forge_cli.py::test_induce_default_folds_is_five`
(added in AA6.1)

### REQ-AUTHOR-052 — Optional feature

WHERE the user runs `forge revise <project>
[--retracted-paper <id>]... [--contradicting-atom <id>]...
[--dry-run]`, the CLI SHALL call
`_agm_revision.revise_theory(induced_path, prov_path,
retracted_docs=<list>, contradicting_atoms=<list>)` from
Phase Z and SHALL print the returned `RevisionReport` with
sections for status counts, status transitions, and (when
present) the full-quarantine warning banner. At least one of
`--retracted-paper` and `--contradicting-atom` SHALL be
required; passing neither SHALL raise `RevisionInputError`
rendered through the `_cli_errors.interpret` table.

**Rationale:** The repeatable flag pattern lets an author
revise on a batch of retractions or contradicting atoms in
one call; surfacing the full-quarantine warning as a banner
makes the alarm impossible to miss; requiring at least one
input prevents an accidental no-op revision that would
otherwise look like a successful run.
**Tested by:**
`tests/test_forge_cli.py::test_revise_happy_path`,
`tests/test_forge_cli.py::test_revise_requires_at_least_one_input`
(added in AA6.4-AA6.5)

### REQ-AUTHOR-053 — Optional feature

WHERE the user runs `forge theory <project>`, the CLI SHALL
print: total rule count; status distribution (`:active` /
`:tentative` / `:quarantined` counts); average entrenchment
across all rules; total induction cost USD; and the top-5
most-cited source documents with the per-document rule
count. WHERE `--rule <id>` is additionally passed, the CLI
SHALL render every `:prov/*` field on the named rule
(status, entrenchment, support sizes, contradiction set,
proposer, validator runs, repair-call count, cost, semantic
neighbours). When the sidecar is missing or malformed
(REQ-PROV-044), the CLI SHALL surface the structured error
and SHALL still render the rule list from
`induced-theory.edn` with empty provenance.

**Rationale:** The aggregate view is the
"what state is the theory in?" answer authors ask
post-`forge induce`; the deep-dive is the
"why does this specific rule exist?" answer they ask
during audit. Continuing to render the rule list on a
malformed sidecar preserves auditability — the rules
themselves are valid even if their provenance is corrupted.
**Tested by:**
`tests/test_forge_cli.py::test_theory_aggregate_and_deep_dive`,
`tests/test_forge_cli.py::test_theory_renders_rules_with_missing_sidecar`
(added in AA6.6)

### REQ-AUTHOR-054 — Unwanted behaviour

IF `forge induce` is invoked on a project where Phase Q's
semantic index (`_semantic_index`) has not been built (the
project's index file is absent), THEN the CLI SHALL print a
warning of the form `warning: semantic index not found at
<path>; running pure-symbolic induction (no atom clustering,
no semantic neighbours).` and SHALL proceed with the
induction; the resulting sidecar SHALL omit
`:prov/semantic-neighbours` on every rule (per the optional
field semantics of REQ-PROV-042).

**Rationale:** The semantic index is advisory — it helps the
inducer cluster atoms before LLM proposal and enriches each
rule's provenance with "see also" neighbour atoms, but
pure-symbolic induction over the Cozo atomspace remains
correct without it. Warning rather than failing means an
author exploring a new project doesn't have to build the
index before they can run the inducer.
**Tested by:**
`tests/test_forge_cli.py::test_induce_warns_when_semantic_index_absent`
(added in AA6.3)

### REQ-AUTHOR-055 — Ubiquitous

Each of `induce`, `revise`, `theory` SHALL have at least
two unit tests in `tests/test_forge_cli.py`: one exercising
the happy path on a fixture verifier project, and one
exercising the most-likely error path (`induce` →
orchestrator failure surfaces as `InductionPipelineError`;
`revise` → missing-required-input surfaces as
`RevisionInputError`; `theory` → missing-sidecar
graceful-degrade). The test pattern SHALL mirror the
fixture-based approach Phase U established for
REQ-AUTHOR-046.

**Rationale:** Phase U set the test discipline for the
`forge` CLI; mirroring it for the new subcommands keeps the
regression boundary uniform and the fixture-build pattern
shared. Two tests per subcommand (happy + error) is the
minimum that distinguishes "implemented" from "passes one
trivial case."
**Tested by:**
`tests/test_forge_cli.py::test_induce_happy_path`,
`tests/test_forge_cli.py::test_induce_pipeline_error_renders_user_message`,
`tests/test_forge_cli.py::test_revise_happy_path`,
`tests/test_forge_cli.py::test_revise_requires_at_least_one_input`,
`tests/test_forge_cli.py::test_theory_aggregate_and_deep_dive`,
`tests/test_forge_cli.py::test_theory_renders_rules_with_missing_sidecar`
(added in AA6.1-AA6.6)

### REQ-AUTHOR-056 — Optional feature

WHERE the `--dry-run` flag is passed to `forge induce` or
`forge revise`, the CLI SHALL produce all logging and
summary output exactly as in a real run AND SHALL NOT write
or mutate any file on disk; the `--dry-run` flag SHALL be
absent from `forge theory` because that subcommand is
inherently read-only.

**Rationale:** Authors iterating on prompt templates,
revision inputs, or sidecar layouts need a fast feedback
loop that does not commit changes; `--dry-run` is the
standard discipline for that loop and mirrors the
`--dry-run` flag already used elsewhere in the codebase
(e.g., scaffold dry-run paths).
**Tested by:**
`tests/test_forge_cli.py::test_induce_dry_run_writes_no_files`,
`tests/test_forge_cli.py::test_revise_dry_run_does_not_mutate_sidecar`
(added in AA6.2)
