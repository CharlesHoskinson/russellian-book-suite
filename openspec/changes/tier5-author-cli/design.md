# Design: tier5-author-cli

## CLI library choice — `click`

Three options were on the table: argparse (stdlib), click
(well-established), and typer (typing-first wrapper over click).
We pick `click`. Reasons:

- **Already in the dep tree.** `book-compose` uses click for its
  internal CLI; adding `forge` on the same library keeps the
  package manifest tight.
- **Mature autocomplete.** Click ships shell-completion plumbing
  for bash/zsh/fish out of the box; the schema-aware completions
  for predicate names (§3) hook in via Click's `shell_complete`
  callbacks.
- **Good help text.** `--help` output is the primary onboarding
  surface for first-time authors; click's help formatting is the
  cleanest of the three without extra config.

Typer would give us typed parameters automatically but adds a
transitive dep on `pydantic`; argparse is too bare for the
interactive flows in §2.

## Interactive prompt flow — `add-constraint`

`forge add-constraint` runs an interactive prompt session using
`prompt_toolkit` (already in the dep tree via `book-compose`):

```
Constraint ID [X042-trial-n-agrees]: _
Backend (:z3 / :cozo / :egg) [:z3]: _
Scope (:subject / :corpus) [:subject]: _
Assert form (use Tab for predicate completion):
  > (forall [?t1 ?t2] _
Tolerance for approx= (or skip): 0.01
On-unsat defect ID: D042-trial-data-disagrees
```

Each prompt has:

- A sensible default (in `[...]`), accepting Enter to take it.
- Tab autocomplete sourced from the verifier's
  `booklogic-schema.edn` for the assert form's predicate names.
- A re-prompt on validation failure (e.g., backend not in the
  enum); no silent acceptance of invalid input.

On completion the CLI:

1. Renders the constraint EDN.
2. Appends to `rules/booklogic/constraints.edn`.
3. Runs `make ci`.
4. If `make ci` fails, prints the relevant subset of the build
   log and offers to roll back the append.

The roll-back is a soft action — it strips the just-appended
constraint from `constraints.edn`. The append is conservative:
we don't reformat the rest of the file, only add at end-of-file
with a leading newline.

## Schema-aware autocomplete

The verifier's `rules/booklogic/booklogic-schema.edn` declares
every predicate name and its type (Int, Real, Bool, etc.). The
CLI loads the schema at startup and feeds the predicate name
list into click's completion callback for the `:assert` form
prompt. As the author types `(:tr`, Tab cycles through every
predicate matching the prefix.

The completer is scoped per-verifier: running `forge add-constraint`
from inside `verifiers/osmotic_pressure/` reads that verifier's
schema, not the bermuda one. Detection: walk up from `cwd` looking
for `rules/booklogic/booklogic-schema.edn`.

## `suggest-lifts` — Phase P interop

`forge suggest-lifts <claim-id>` reads the claim's
`canonical_text` from `claims.jsonl`, calls Phase P's `:backend
:llm` provider with a prompt template that asks for "regex
patterns that would extract structured atoms from this prose,"
type-checks each proposal against the schema (does the regex's
named groups produce values of the predicate's declared type?),
and prints the surviving candidates as `deflift` forms.

The CLI does NOT auto-merge into `rules/lifts.edn`. The output is
explicitly for human review — the author copies the desired
candidate into the lifts file. The reason: lifts that look right
to the LLM can still be wrong about the canonical-text's actual
shape; an auto-merge that runs through `make ci` is fast but
makes the lifts surface a magic-comment rather than an editorial
artefact.

## `explain-defect` — Phase S + Phase T interop

`forge explain-defect <defect-id>` reads `work/verdict.edn` for
the defect's unsat core, reads `claims.jsonl` for each core
claim's confidence and source span, reads the source markdown for
the surrounding context, and prints:

```
Defect: D042-trial-data-disagrees (constraint X042-trial-n-agrees)
Severity: hard (declared) / hard (rendered)
Defect confidence: 0.92

Unsat core:
  C042-mizuno-trial-n  conf 0.95  chap-3:4821-4889
    "Mizuno et al. (2008) enrolled 37 patients..."
  C087-mizuno-trial-n  conf 0.92  chap-7:7102-7167
    "...the Mizuno 2008 cohort of 42 patients..."

Interpretation:
  Two chapters cite the same trial with disagreeing patient counts
  (37 vs 42). The cross-chapter constraint X042-trial-n-agrees
  requires equality; one citation is wrong.

See also: docs/booklogic-dsl-reference.md §2.5 (Scope).
```

The "Interpretation" paragraph is generated from a template
keyed on the constraint's `:explanation` field (declared in
`constraints.edn`) — not from an LLM call. Templates keep the
output deterministic and the surface controllable.

## Error surface

Every CLI subcommand wraps its body in a try/except that
catches the framework's named error types (`IngestConfidenceError`,
`IngestRegexDialectError`, `make ci` non-zero exit, etc.) and
renders each as a hand-written message of the shape:

```
ERROR: <one-line summary>

What likely happened: <interpretive paragraph>
Likely fix: <one or two concrete steps>
Reference: docs/booklogic-dsl-reference.md §<n>
```

No stack traces reach the user surface unless `--debug` is
passed. The error-message table lives in
`skills/neurosym-forge/scripts/_cli_errors.py` so new error
types can be added with their interpretive text in one place.

## Installation

`skills/neurosym-forge/pyproject.toml` declares `forge` as a
console-script entry point pointing at `forge_cli:cli`. Authors
install via `pip install -e skills/neurosym-forge` from the
repo root (or `pipx install` for a fresh isolated environment).
