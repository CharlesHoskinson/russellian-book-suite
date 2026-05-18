# Tasks: tier2-strict-regex-dialect

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase E.1 for full
TDD steps. Task numbers correspond 1:1.

## Phase E.1.1 — Strict-dialect gate in ingest

- [ ] E1.1.1: `verifiers/osmotic_pressure/scripts/tests/test_strict_regex_dialect.py::test_js_named_group_raises` (write failing test). (REQ-INGEST-051)
- [ ] E1.1.2: Replace `_to_python_regex` with `_assert_python_regex_dialect` in `ingest_ledger.py`. (REQ-INGEST-050, REQ-INGEST-051)
- [ ] E1.1.3: Re-run pytest — failing test now passes.
- [ ] E1.1.4: Add `test_python_named_group_compiles_unchanged` asserting `(?P<v>)` ingests cleanly. (REQ-INGEST-050)

## Phase E1.2 — Compose with the OPAQUE-fraction gate

- [ ] E1.2.1: Add `test_opaque_gate_still_fires_on_non_matching_regex` ensuring a regex that simply does not match (no JS-form) still trips REQ-INGEST-041. (REQ-INGEST-052)

## Phase E1.3 — Upgrade the bug7 regression

- [ ] E1.3.1: Rename `test_bug7_regex_break_caught_by_extract_gate` to `test_bug7_js_named_group_caught_by_dialect_gate`.
- [ ] E1.3.2: Mutate a baked project's `lifts.edn` to introduce `(?<v>...)` (the actual sprint-5 bug shape) and assert `make ci` fails at the dialect gate before reaching `make extract`. (REQ-INGEST-053)

## Phase E1.4 — Doc + commit

- [ ] E1.4.1: Update `references/grounded-atoms.md` § Regex dialect with the strict-error message and dialect rationale.
- [ ] E1.4.2: Commit `openspec(tier2): strict regex dialect change folder (REQ-INGEST-050..053)` once specs land.
