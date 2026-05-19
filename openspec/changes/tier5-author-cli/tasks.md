# Tasks: tier5-author-cli

See `docs/plans/2026-05-19-tier5-scale-author.md` Phase U for full
TDD steps. Task numbers track that document.

## Phase U.1 — Skeleton + packaging

- [ ] U1.1: New `skills/neurosym-forge/scripts/forge_cli.py`
  exposing a click `Group` named `cli` with five subcommands
  (`add-constraint`, `suggest-lifts`, `explain-defect`,
  `similar`, `render`). (REQ-AUTHOR-040)
- [ ] U1.2: `skills/neurosym-forge/pyproject.toml` declares
  `[project.scripts] forge = "forge_cli:cli"`; verify
  `pip install -e skills/neurosym-forge` succeeds in a fresh
  venv. (REQ-AUTHOR-046)

## Phase U.2 — `add-constraint`

- [ ] U2.1: Interactive prompt session using prompt_toolkit;
  prompts for id, backend (default `:z3`), scope (default
  `:subject`), assert form, tolerance, on-unsat. (REQ-AUTHOR-041)
- [ ] U2.2: Schema-aware autocomplete: load
  `rules/booklogic/booklogic-schema.edn` from the current verifier
  (walk up from cwd) and feed predicate names into the assert-form
  completer.
- [ ] U2.3: On completion, render EDN, append to
  `rules/booklogic/constraints.edn`, run `make ci`; on failure
  print the relevant build-log slice and offer rollback.

## Phase U.3 — `suggest-lifts`

- [ ] U3.1: Read claim's `canonical_text` from `claims.jsonl`,
  call Phase P's LLM provider with the regex-suggestion prompt
  template, type-check proposals against the schema's predicate
  types, print surviving candidates as `deflift` forms.
  (REQ-AUTHOR-042)
- [ ] U3.2: Explicitly do NOT auto-merge into `rules/lifts.edn`;
  output is for human review.

## Phase U.4 — `explain-defect`

- [ ] U4.1: Read `work/verdict.edn` for defect, walk unsat core,
  read each claim's confidence and source span from
  `claims.jsonl` and source markdown; render the structured
  output per design.md §6. (REQ-AUTHOR-043)
- [ ] U4.2: Generate the "Interpretation" paragraph from a
  template keyed on the constraint's `:explanation` field;
  deterministic, no LLM call.

## Phase U.5 — `similar`

- [ ] U5.1: Call Phase Q's `similar_claims(claim_id, k=N)` and
  print top-k as a table with columns: claim_id, similarity
  score, subject, canonical_text snippet. (REQ-AUTHOR-044)
- [ ] U5.2: Default `k=5`, override via `--k <int>`.

## Phase U.6 — `render`

- [ ] U6.1: Thin wrapper over Phase T's `render_annotations.py`
  exposing it as `forge render <manuscript.md>`; forwards
  `--annotations`, `--out-dir`, `--stylesheet` flags through.
  (REQ-PUB-044 from Phase T)

## Phase U.7 — Error surface

- [ ] U7.1: New `skills/neurosym-forge/scripts/_cli_errors.py`
  table maps framework error types to interpretive messages with
  "Likely fix" and "Reference" sections. Every subcommand wraps
  its body in a try/except routing through the table; no stack
  traces unless `--debug` is passed. (REQ-AUTHOR-045)

## Phase U.8 — Fixture-based tests

- [ ] U8.1: `tests/test_forge_cli.py` covers each subcommand:
  happy path on a fixture verifier project + the most likely
  error path (e.g., missing claim id, malformed assert).
  (REQ-AUTHOR-046)

## Phase U.9 — Docs

- [ ] U9.1: `docs/booklogic-dsl-reference.md` gains a §10
  "Author CLI" subsection listing every subcommand with a short
  example invocation.
- [ ] U9.2: `skills/neurosym-forge/SUPPORT_MATRIX.md` lists each
  CLI subcommand as `wired`.

## Phase U.10 — PR

- [ ] U10.1: Push `plan/tier5-scale-author` (author-cli slice)
  and open the PR.
- [ ] U10.2: Merge on green CI.
