# Design: booklogic-pr5-bermuda-migration

## Architecture pointer

Full TDD-shaped detail at `docs/plans/2026-05-17-booklogic-pr5.md`.

## Key decisions

- Five existing Bermuda predicates (`parishes`, `named_islands`, `currency_peg`,
  `airport_island`, `cedar_binomial`) migrate verbatim to BookLogic source.
- Four new quantitative predicates added: `population`, `land-area-km2`,
  `gdp-usd-billion`, `hospital-beds-kemh`.
- `canonical.rs` asserts five facts today: parishes=9, islands=181, BMD/USD
  parity, L. F. Wade on St. David's, cedar = Juniperus bermudiana. Each
  becomes a `defconstraint` in `rules/constraints.edn`.
- Z3 build canonical gate: `ubuntu-latest` CI with `bundled` Z3. Local
  Windows build best-effort; if it fails, capture diagnostics and continue.
- The ch-02 drift target is line 44 of
  `examples/bermuda-manual/book/releases/6.0.0/chapter-bundles/ch-02-v6/draft.md`
  ("Richard Norwood divided the colony into eight parishes"). The ledger
  claim `clm-2026-000008` says nine.

## Risks

- Z3 bundled build cold-builds C++ from source on CI's first run.
  `Swatinem/rust-cache@v2` primes for subsequent runs.
- PR-4's `defconstraint` codegen must emit `axioms.rs` deterministically;
  if it doesn't, Phase 2 surfaces the gap.

## Open questions

None.
