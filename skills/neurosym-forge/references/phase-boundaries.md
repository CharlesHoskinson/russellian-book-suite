# Phase boundaries

```
Phase 1 [Claude]         Extract atoms              -> work/claims.edn
Phase 2 [ClojureScript]  Rewrite via meander         -> work/fol.edn
Phase 3 [Rust]           Verify (Z3 / egg / cozo)    -> work/verdict.edn
Phase 4 [Claude]         Synthesise report           -> work/report.md
Phase 5 [Rust]           Typeset (tectonic)          -> work/report.pdf
```

## What crosses each boundary

| Boundary | Wire format | Owner of validation |
|---|---|---|
| Claude → CLJS | EDN file `work/claims.edn` matching atom.schema.json | `lint_atomspace.py` |
| CLJS → Rust | EDN string over napi-rs | malli post-condition on CLJS side, `parse_formulas` on Rust side |
| Rust → CLJS | EDN string over napi-rs | serde + edn-rs in Rust, malli pre-condition on CLJS |
| CLJS → Claude | EDN file `work/verdict.edn` | malli on CLJS write |
| Claude → Rust | LaTeX string + path | tectonic accepts as-is |

## Failure modes

- `:unsat` from Phase 3 — Claude must re-enter Phase 1 with a corrected claim set; up to 3 attempts then escalate.
- `:unknown` from Phase 3 — Z3 timed out. Bump `:smt-timeout-ms` in `work/config.edn`.
- malli DbC violation — phase script throws `ex-info`; the orchestrator emits an EDN error record.
