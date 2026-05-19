# Change: tier5-author-cli

**Tier:** 5 of 5 (scale + author-facing tier)
**Branch:** `plan/tier5-scale-author`
**Depends on:** Tier 1-4 landed; composes with Phase P (LLM
extractors), Phase Q (semantic retrieval), Phase T (publication
bridge)

## Why

`docs/booklogic-dsl-reference.md` is 1146 lines. The Phase N
onboarding bench surfaced consistent failure modes when fresh
agents try to add a new constraint, lift an unmatched claim, or
debug a `:unsat` verdict: they get lost in the reference doc,
they paste partial forms, they hand-traverse unsat cores without
seeing the underlying confidence chain, and they re-cite claims
they've already cited because the corpus is too big to grep.

Each of those failures has a mechanical answer: a prompt for the
fields you have to fill in, a regex-suggester for unmatched
claims, a defect explainer that traces the unsat core, and a
similarity probe over claims.jsonl. The framework already has the
pieces — Phase P's LLM provider, Phase Q's `similar_claims`,
Phase S's confidence propagation, Phase T's defect surfacing. The
gap is an interactive surface that composes them.

## What

- `skills/neurosym-forge/scripts/forge_cli.py` ships subcommands:
  `add-constraint`, `suggest-lifts`, `explain-defect`,
  `similar`, `render`.
- `add-constraint` prompts for constraint id, backend, assert
  form (with schema-aware autocomplete), tolerance, and
  `:on-unsat` defect id; appends to `rules/booklogic/constraints.edn`
  and runs `make ci` to confirm the new constraint compiles.
- `suggest-lifts <claim-id>` calls Phase P's LLM provider to
  propose regex patterns for unmatched claims; type-checks
  against the schema; emits candidate `deflift` forms for human
  review.
- `explain-defect <defect-id>` displays the defect's source span
  with surrounding context, the unsat core's claim chain, each
  claim's confidence, and a one-paragraph interpretation.
- `similar <claim-id>` calls Phase Q's `similar_claims` and
  prints top-k as a table.
- Framework errors surface as hand-readable messages with a
  most-likely-fix and a DSL reference link; no stack traces in
  the user surface.
- The CLI installs via `pip install -e skills/neurosym-forge`.

## Capabilities touched

- `author-cli` — NEW (adds REQ-AUTHOR-040..046)

## Implementation notes

See `docs/plans/2026-05-19-tier5-scale-author.md`, Phase U.

## Acceptance

- 7 REQ-AUTHOR IDs ship in `specs/author-cli/spec.md`.
- `forge --help` exposes every subcommand with non-trivial help.
- Each subcommand has a fixture-based pytest exercising the
  happy path and the most likely error path.
- `pip install -e skills/neurosym-forge` succeeds against a
  fresh venv.
