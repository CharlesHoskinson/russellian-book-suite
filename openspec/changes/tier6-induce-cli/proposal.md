# Change: tier6-induce-cli

**Tier:** 6 of 7 (theory-induction tier)
**Branch:** `plan/tier6-theory-induction`
**Depends on:** Tier 5 phase U (`author-cli` baseline);
Tier 6 phases V (induction-grammar), W (candidate-generation),
X (smt-numeric-fitting), Y (provenance-sidecar), Z
(agm-revision)

## Why

Tier 6 introduces an inducer (Phase V/W/X), a provenance
sidecar (Phase Y), and an AGM-compliant revision algorithm
(Phase Z). Each lives behind a Python or CLJS module surface.
A human author cannot run them without a user-facing
command. Phase U shipped `forge add-constraint`,
`forge suggest-lifts`, etc.; Tier 6 needs the same `forge`
prefix to land three new subcommands so an author moves
between hand-authored and induced constraints under one
binary.

## What

- Three new subcommands on `forge`:
  - `forge induce <project>` — run the induction pipeline
    (nbb orchestrator + grammar enforcer + candidate
    generator + SMT fitter), emit
    `rules/booklogic/induced-theory.edn` and
    `induced-theory.prov.edn`, print a one-screen summary.
  - `forge revise <project>
    [--retracted-paper <id>] [--contradicting-atom <id>]`
    — call `_agm_revision.revise_theory(...)` and print
    the `RevisionReport`.
  - `forge theory <project> [--rule <id>]` — inspect the
    induced theory and sidecar; aggregate summary by default,
    deep-dive on one rule with `--rule`.
- All three flow through the existing `_handle` error
  decorator and the `_cli_errors.interpret` table.
- A `--dry-run` flag on `induce` and `revise` produces all
  logging output without writing any files.

## Capabilities touched

- `author-cli` — EXTEND (adds REQ-AUTHOR-050..056 on top of
  Phase U's REQ-AUTHOR-040..046)

## Implementation notes

See `docs/plans/2026-05-19-tier6-theory-induction.md`,
Phase AA.

## Acceptance

- 7 REQ-AUTHOR IDs (050-056) ship in
  `specs/author-cli/spec.md`.
- `forge induce`, `forge revise`, `forge theory` each
  surface in `forge --help` with non-trivial subcommand
  help.
- Each subcommand has a fixture-based pytest exercising the
  happy path and at least one error path.
- `--dry-run` produces stdout output but no file writes.
