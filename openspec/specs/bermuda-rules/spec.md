# Capability: bermuda-rules

The Bermuda verifier's BookLogic source set at `verifiers/bermuda/rules/`,
covering the five existing predicates (`parishes`, `named_islands`,
`currency_peg`, `airport_island`, `cedar_binomial`) and four new quantitative
predicates (`population`, `land-area-km2`, `gdp-usd-billion`,
`hospital-beds-kemh`). After full migration, `canonical.rs` is deleted and
`axioms.rs` is the BookLogic codegen output.

Sprints booklogic-cleanup (D1 hygiene on seed.edn + grounded.edn) and
booklogic-pr5-bermuda-migration (full rewrite) add REQs.

## Requirements

_(none yet)_
