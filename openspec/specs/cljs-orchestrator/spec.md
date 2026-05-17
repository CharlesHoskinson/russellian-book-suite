# Capability: cljs-orchestrator

The ClojureScript orchestrator at `verifiers/bermuda/cljs-orchestrator/`,
comprising six modules (`bridge`, `core`, `ir`, `nl_to_fol`, `phases`,
`unify`) plus the `shadow-cljs` build and test targets. Owns the CLI
dispatch (`translate` / `verify` / `typeset`), the malli schemas for
`Atom`, `Formula`, `Claim`, `Verdict`, the meander `Claim → Formula`
rewrite, and the napi bridge to the Rust verifier.

Sprints booklogic-cleanup (test harness + bug fix),
booklogic-d2-wiring (event-aware translate), and
booklogic-pr5-bermuda-migration (verify subcommand on real Z3) add REQs.

## Requirements

_(none yet)_
