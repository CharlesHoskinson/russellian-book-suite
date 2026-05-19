# Capability delta: author-cli — change: tier5-author-cli

This change introduces a new capability `author-cli`, an
interactive `forge` command that walks authors through the
framework's common workflows: adding a constraint, suggesting
lifts for unmatched claims, debugging a `:unsat` verdict,
probing for similar claims, and rendering annotations. The CLI
composes Phase P (LLM extractors), Phase Q (semantic retrieval),
Phase S (confidence propagation), and Phase T (publication
bridge) behind a single user surface.

## ADD

### REQ-AUTHOR-040 — Ubiquitous

The framework SHALL ship
`skills/neurosym-forge/scripts/forge_cli.py` exposing a click
`Group` named `cli` with subcommands: `add-constraint`,
`suggest-lifts`, `explain-defect`, `similar`, and `render`. The
group SHALL be exposed as the console-script entry point
`forge` via `skills/neurosym-forge/pyproject.toml`.

**Rationale:** A single binary surface that covers the five most
common authoring tasks reduces the friction the Phase N
onboarding bench measured; click's group/subcommand pattern
keeps each task's help text and flags discoverable independently
via `forge <subcommand> --help`.
**Tested by:**
`tests/test_forge_cli.py::test_all_subcommands_exposed`
(added in U1.1)

### REQ-AUTHOR-041 — Optional feature

WHERE the user runs `forge add-constraint`, the CLI SHALL drive
an interactive prompt session asking in order for: constraint
id, backend (`:z3` default, `:cozo` and `:egg` accepted), scope
(`:subject` default, `:corpus` accepted per Phase R), an
`:assert` form (with Tab-autocomplete against the verifier's
`booklogic-schema.edn` predicate names), tolerance (for
`approx=`, skippable), and the `:on-unsat` defect id. On
completion the CLI SHALL render the constraint EDN, append it to
`rules/booklogic/constraints.edn`, and run `make ci`; on `make
ci` failure the CLI SHALL print the relevant build-log slice and
offer to roll back the append.

**Rationale:** The constraint surface is the most error-prone in
the DSL because it composes backend, scope, assert form, and
defect plumbing; prompting field-by-field with schema-aware
autocomplete eliminates the "I pasted the wrong predicate name"
class of errors. Running `make ci` immediately closes the
feedback loop; the rollback offer keeps the file clean if the
new constraint doesn't compile.
**Tested by:**
`tests/test_forge_cli.py::test_add_constraint_appends_and_runs_ci`
(added in U2.3)

### REQ-AUTHOR-042 — Optional feature

WHERE the user runs `forge suggest-lifts <claim-id>`, the CLI
SHALL read the claim's `canonical_text` from `claims.jsonl`,
call Phase P's `:backend :llm` provider with a regex-suggestion
prompt, type-check each proposed regex's named groups against
the schema's predicate types, and emit the surviving candidates
as formatted `deflift` forms to stdout. The CLI SHALL NOT
automatically merge proposals into `rules/lifts.edn`; the output
SHALL be explicitly for human review.

**Rationale:** LLM-proposed lifts can look right but be wrong
about the canonical-text's actual shape; an auto-merge would
make the lifts file a magic-comment surface rather than an
editorial artefact authors review. Type-checking against the
schema filters the lowest-quality proposals before they reach
the author's screen.
**Tested by:**
`tests/test_forge_cli.py::test_suggest_lifts_emits_candidates_no_auto_merge`
(added in U3.1)

### REQ-AUTHOR-043 — Optional feature

WHERE the user runs `forge explain-defect <defect-id>`, the CLI
SHALL display: the defect's source span with surrounding
context, the unsat core's claim chain with each claim's
confidence (per Phase S), the defect's
`:defect-confidence` and `:declared-severity` /
`:severity` (post-downgrade), and a one-paragraph
human-readable interpretation generated from a template keyed on
the constraint's `:explanation` field. The interpretation
SHALL be deterministic — no LLM call at explain time.

**Rationale:** Hand-tracing an unsat core today means reading
EDN, then JSONL, then markdown, then constraints.edn; rolling
the chain into a single rendered output is the mechanical fix
for the most common Phase N onboarding-bench failure. Keeping
the interpretation template-driven makes the output reproducible
and the surface controllable.
**Tested by:**
`tests/test_forge_cli.py::test_explain_defect_renders_chain_and_interpretation`
(added in U4.1)

### REQ-AUTHOR-044 — Optional feature

WHERE the user runs `forge similar <claim-id> [--k N]`, the CLI
SHALL call Phase Q's `similar_claims(claim_id, k=N)` (default
`k=5`) and print the top-k results as a table with columns:
`claim_id`, similarity score, subject, and a canonical-text
snippet.

**Rationale:** Authors working in a large corpus repeatedly hit
"did I cite this already?"; a similarity probe over the claim
embedding store gives them an answer in one command instead of a
grep that misses paraphrases.
**Tested by:**
`tests/test_forge_cli.py::test_similar_prints_top_k_table`
(added in U5.1)

### REQ-AUTHOR-045 — Unwanted behaviour

IF a CLI subcommand hits a framework error (compile failure,
ingest validation, `make ci` non-zero exit, missing fixture
file), THEN the CLI SHALL render a hand-readable message of the
shape `ERROR: <summary> / What likely happened: ... / Likely
fix: ... / Reference: docs/booklogic-dsl-reference.md §<n>` and
SHALL NOT print a Python stack trace to stdout or stderr. The
mapping from framework error types to interpretive messages
SHALL live in `skills/neurosym-forge/scripts/_cli_errors.py`. A
`--debug` flag SHALL re-enable stack traces for developer
diagnosis.

**Rationale:** First-time authors react to stack traces by
abandoning the tool; the four-line interpretive surface gives
them a concrete next step. Centralising the table in one module
keeps the error-message library reviewable as a single artefact.
**Tested by:**
`tests/test_forge_cli.py::test_framework_error_renders_user_message_no_traceback`
(added in U7.1)

### REQ-AUTHOR-046 — Ubiquitous

The CLI SHALL be installable via `pip install -e
skills/neurosym-forge` (or equivalent) in a fresh Python
virtualenv; a test suite SHALL exercise each subcommand against
fixture inputs (happy path and one error path each), and the
`pip install` step SHALL be exercised in CI on the same Python
versions the rest of the framework supports.

**Rationale:** A CLI that only works in the contributor's home
shell isn't shippable; the install-in-fresh-venv test is what
catches missing dependencies, broken entry points, and path
assumptions before they reach an author. The per-subcommand
fixture coverage keeps regressions narrow.
**Tested by:**
`tests/test_forge_cli_install.py::test_pip_install_e_succeeds_in_clean_venv`,
`tests/test_forge_cli.py::test_each_subcommand_happy_and_error_path`
(added in U1.2, U8.1)
