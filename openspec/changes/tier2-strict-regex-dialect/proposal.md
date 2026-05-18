# Change: tier2-strict-regex-dialect

**Tier:** 2 of 4 (general-purpose framework hardening)
**Branch:** `feat/tier2-strict-regex-dialect`
**Depends on:** tier1-fact-extraction-preview (REQ-INGEST-040..048)

## Why

`verifiers/osmotic_pressure/scripts/ingest_ledger.py` ships a silent
JS→Python regex converter (`_to_python_regex`, ~line 80) that rewrites
`(?<name>...)` to `(?P<name>...)` on every match attempt. That
converter is the exact "be liberal in what you accept, fail silently"
pattern Tier 1's audit identified as the root cause of the sprint-5
regex incident: a lift author writes a JS-form regex by accident, the
converter silently fixes it for the Python ingester, and the CLJS
compiler — which uses real JS `RegExp` — sees a different pattern. The
two pipelines now disagree about what gets extracted, and the
disagreement is invisible.

The Tier 1 regression test (`test_bug7_js_named_group_caught_by_extract_gate`,
REQ-INGEST-048) had to surrogate around this: it asserts the extract
gate catches a *separately* introduced regex break, because the obvious
mutation — the JS-style named group itself — is silently repaired.

## What

- Replace `_to_python_regex(pat)` with `_assert_python_regex_dialect(pat)`:
  same call site, but raises `EdnReadError` on any JS-form named group,
  pointing the author at `references/grounded-atoms.md` § "Regex dialect"
  for the Python-form spelling.
- Update REQ-INGEST-048's regression fixture to use a real `(?<v>)`
  mutation, completing the gate path the surrogate test could not cover.
- The existing OPAQUE-fraction gate (REQ-INGEST-041) is unchanged; this
  change adds a strict-input gate *before* it, so authors get the most
  specific error first.

## Capabilities touched

- `edn-boundary` — MODIFY (adds strict-dialect gate at the ingest input
  boundary; the regex dialect is part of the cross-language EDN contract
  that already covers `_edn_reader`/`_edn_writer`)

## Implementation notes

See `docs/plans/2026-05-18-tier234-and-usefulness.md`, Phase E.1.

## Acceptance

- A predicates.edn that uses `(?<v>)` raises an `EdnReadError`-shaped
  exception at ingest with a clear pointer to the Python dialect doc.
- A predicates.edn that uses `(?P<v>)` ingests cleanly, identical to
  current behaviour, with no silent rewriting.
- The bug7 regression test now exercises the genuine `(?<v>)` mutation
  end-to-end through `make ci`.
