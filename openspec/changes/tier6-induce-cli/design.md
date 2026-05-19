# Design: tier6-induce-cli

## Subcommand surfaces

### `forge induce`

```
forge induce <project> [--folds N] [--budget-usd N] [--dry-run]
```

Arguments:

- `<project>` — path to a verifier project (e.g.,
  `verifiers/adsc-clinical/`). Walks up from cwd if omitted.
- `--folds N` — number of document-held-out folds for
  validation; default `5`.
- `--budget-usd N` — opt-in dollar ceiling across the
  induction run; no default. When the running cost exceeds
  the budget, the inducer stops accepting new candidates and
  emits whatever it has.
- `--dry-run` — produces all logging output but writes no
  files.

Behavior:

1. Locate the project's `claims.jsonl`, schema, and existing
   sidecar.
2. Shell out to `nbb scripts/induce_theory.cljs` (the nbb
   orchestrator from Phase W) with the project path + flags.
3. The orchestrator drives the grammar enforcer (Phase V),
   candidate generator (Phase W), SMT fitter (Phase X), and
   provenance writer (Phase Y).
4. On completion, emit
   `rules/booklogic/induced-theory.edn` and
   `rules/booklogic/induced-theory.prov.edn`.
5. Print a one-screen summary:
   - Total rules induced.
   - Total cost USD.
   - Top-3 highest-entrenchment rules with their rule-id +
     entrenchment + support-doc-count.

### `forge revise`

```
forge revise <project> [--retracted-paper <id>]...
                       [--contradicting-atom <id>]...
                       [--dry-run]
```

Arguments:

- `<project>` — verifier path (as above).
- `--retracted-paper <id>` — repeatable; accumulates into
  `retracted_docs` for `revise_theory(...)`.
- `--contradicting-atom <id>` — repeatable; accumulates into
  `contradicting_atoms`.
- `--dry-run` — load the sidecar and run the revision in
  memory; print the `RevisionReport`; do not write the
  sidecar back.

At least one of `--retracted-paper` or
`--contradicting-atom` must be passed; click enforces the
"at least one" constraint via a `@click.argument` callback.

Behavior:

1. Load `induced-theory.edn` + `induced-theory.prov.edn`.
2. Call `_agm_revision.revise_theory(...)`.
3. Print the `RevisionReport`:
   ```
   Revision summary:
     Rules affected:       3
     Rules active:        12
     Rules tentative:      4
     Rules quarantined:    2

   Status transitions:
     :induced/herd-immunity-threshold  :active -> :tentative
     :induced/vaccine-efficacy-r0      :active -> :quarantined
     :induced/trial-cohort-size        :tentative -> :quarantined
   ```
4. If `RevisionReport.full_quarantine_warning`, prepend a
   warning banner before the summary.

### `forge theory`

```
forge theory <project> [--rule <id>]
```

Arguments:

- `<project>` — verifier path.
- `--rule <id>` — deep-dive into one rule.

Aggregate output:

```
Theory summary for verifiers/adsc-clinical:
  Rules:               18
  Status:              :active 12  :tentative 4  :quarantined 2
  Average entrenchment: 0.71
  Total induction cost: $0.42

Top-5 most-cited source documents:
  pmid:12345    7 rules
  pmid:67890    5 rules
  pmid:11111    4 rules
  pmid:22222    3 rules
  pmid:33333    3 rules
```

`--rule <id>` deep-dive:

```
Rule :induced/herd-immunity-threshold
  Status:        :active
  Entrenchment:  0.83
  Support:       112 atoms across 37 documents
  Contradicts:   4 atoms (advisory)
  Proposed by:   :llm  model=claude-haiku-4-5  provider=:anthropic
  Validated by:  :z3 (5-fold, sat-rate 0.89, tolerance 0.043)
                 :cozo (support-rate 0.94)
  Repair calls:  2
  Cost:          $0.018
  See also:      c-203, c-411 (semantic neighbours)
```

## `--dry-run` composition with `_handle`

The existing `_handle` decorator from Phase U wraps every
subcommand body in a try/except routing through
`_cli_errors.interpret`. `--dry-run` operates AT the
subcommand body, not at the decorator: the body parses
flags, performs all logging, and short-circuits before the
file-write call. Error handling is unchanged — if the dry
run hits a framework error (e.g., missing sidecar), the
error surfaces through `_handle` exactly as it would in a
real run.

The flag exists for debugging: an author iterating on the
inducer's prompt template can run `forge induce --dry-run`
to see the candidate set and cost trace without committing
to the sidecar mutation. Symmetric on `revise`.

## Semantic-index degraded mode

`forge induce` consults Phase Q's `_semantic_index` for two
optional behaviours: (a) atom-cluster pre-grouping before
LLM proposal; (b) semantic-neighbours enrichment on each
rule's provenance entry. If the index is absent (the project
hasn't run `forge build-index`), the CLI SHALL warn:

```
warning: semantic index not found at <path>; running pure-symbolic
induction (no atom clustering, no semantic neighbours).
```

and proceed. The inducer still produces valid rules; only
the advisory enrichment is skipped. This is REQ-AUTHOR-054.

## Integration with Phase U's error UX

Each new subcommand wraps its body in `@_handle`. The
existing `_cli_errors.interpret` table gains entries for
new error types this tier introduces:

- `ProvenanceSidecarError` (from Phase Y) — pointer at the
  sidecar file path.
- `RevisionInputError` — when both
  `--retracted-paper` and `--contradicting-atom` are
  omitted from `forge revise`.
- `InductionPipelineError` — when the nbb orchestrator
  exits non-zero; surfaces the orchestrator's tail stdout
  with a pointer at the candidate-fail log.

Each entry follows the four-line format Phase U
established: `ERROR: ... / What likely happened: ... /
Likely fix: ... / Reference: ...`.

## Why three subcommands, not one with a `--mode` flag?

`induce`, `revise`, and `theory` have disjoint argument
sets and disjoint failure modes. Bundling them under one
subcommand with `--mode induce | revise | theory` would
push the per-mode flag set into a single help screen and
make the most common mistakes (missing `--retracted-paper`
on revise; missing the project path) harder to surface.
Three subcommands keep the `forge <sub> --help` surface
narrow and discoverable.
