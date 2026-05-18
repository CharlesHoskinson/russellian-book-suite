# Change: tier1-fact-extraction-preview

**Tier:** 1 of 4 (the silent-wrong-`:sat` triage)
**Branch:** `feat/tier1-fact-extraction-preview`
**Depends on:** none

## Why

The single most damaging onboarding-and-correctness failure mode is the
`:OPAQUE` fallthrough: a `deflift` regex fails to match (wrong dialect,
typo, apostrophe-after-space), no fact is extracted for that predicate,
the SMT axiom's `Real::new_const(...)` symbol stays unbound, the solver
trivially returns `:sat`, and **nothing tells the author anything went
wrong**. The sprint-5 doctored-fixture bug, the JS-vs-Python regex
incident, and the `:sol`-vs-`?s` subject-naming bug were all instances
of this class.

There is no current way to inspect what facts ingest actually extracted
short of reading the intermediate `claims.edn` by hand or running the
verifier with `VERIFIER_DEBUG_SMT=1` and reading raw Z3 SMT-LIB.

## What

- A `scripts/extract_preview.py` tool that takes a ledger JSONL + a
  predicates.edn and prints a per-predicate fact-count summary plus the
  total `:OPAQUE` count. Exits non-zero with a prominent message if
  the OPAQUE fraction exceeds a threshold (default 50 %).
- A `make extract CLAIMS=<file>` Makefile target per verifier that
  invokes the preview against a chosen fixture.
- The scaffold template's `Makefile.tmpl` gains the same target so every
  new verifier starts with the preview wired.
- `make ci` invokes `make extract` against the project's primary
  fixture before invoking `pytest`, so a CI run that would have silently
  passed via OPAQUE-fallthrough now fails loudly at the extract gate.
- A dry-run flag `--dry-run` on the preview prints the EDN that *would*
  have been written, without touching `work/claims.edn`.

## Capabilities touched

- `ingest-trace` — MODIFY (adds REQs for extract-preview + OPAQUE gate)

## Implementation notes

See `docs/plans/2026-05-18-tier1-general-purpose.md`, Phase A.

## Acceptance

- A doctored fixture with a JS-style `(?<v>)` regex in lifts triggers
  the OPAQUE-fraction gate during `make ci` instead of producing a
  spurious `:sat`.
- A normal clean fixture under the threshold prints a fact-count table
  and proceeds.
- The scaffold template instantiates the preview target.
