# Reconciliation vs the 2026-05-29 suite-wide audit

The prior audit confirmed **115 findings (7 critical, 29 high, 41 medium, 35 low, 3 info)**. This pass re-checked them in current code. Headline: **the Python-skill criticals are all fixed; the verifier-chain criticals are half-fixed.**

## Prior CRITICALS (7)

| Prior critical | Status now | Evidence |
|---|---|---|
| book-qa sentinel routes D9–D13 to soft gate | **FIXED** | `sentinel.py:30-33` hard-fails D9/D10/D11/D13; regression tests `test_critical_d9_d13_are_hard_fail`, `test_d12_stays_soft`. |
| Branch-protection requires non-existent job names | **FIXED + guarded** | single `ci-required` context; `check-required-name.sh` enforces agreement; `merge_group:` present. |
| cljs `nl_to_fol` nested tree vs Rust flat atoms | **HALF-FIXED** | fixed in bermuda+adsc; **STILL OPEN in epidemiology + osmotic (C-001/C-002)**. |
| `phases/verify` bare vector vs `{:atoms}` | **HALF-FIXED** | same split. |
| `kg.rs` queries undefined relations → Err | **FIXED** | bermuda creates relations; epi/osmotic/adsc dropped the query. (But kg now runs on empty `v.verified` — new H-03.) |
| adsc `smt.rs` missing `Edn::UInt` arm → false sat | **FIXED** | all 4 have the UInt arm + tests. |
| (7th critical, verifier-chain cluster) | **partially** | the chain is repaired in 2 of 4 crates; the structural copy-drift root cause remains. |

## Prior HIGH — representative status

**FIXED (verified):** propagate-ignores-derivation-edges, propagate-iteration-dead, infer-kind-reads-absent-path (book-knowledge); dedup-substring-drops-distinct-findings, severity-counts-from-dedup, findings-10plus-dropped, missing-gating-false-pass (review/QA); holdout-ignores-candidate, phase-v-import-fails, generators-emit-unsupported-ops, grammar-gate-never-invoked (neurosym-forge); autodetect-latest-by-mtime, orphan-citation-strip, preflight-chapter-conformance, persona-gate-trivial-pass (book-compose); 6 of 7 russellian-style linter findings; build-russell-corpus cli-llm-unwired + sentinel-dedup.

**STILL OPEN:**
- `holdout-validation-not-wired` → fix landed in the test-only Python orchestrator; `forge induce` runs the CLJS path which still has no holdout/tautology gate (H-01).
- `tautology-circular-only-in-test-stubs` → circular-def fixed; tautology gate still has zero production callers (H-01).
- `datalog-detectors-mismatch-real-ledger` → detectors still read non-schema `value`/`implies`; inert on a real ledger (H-05).
- `real-manuscript-no-carriers` → book-compose still emits no supports carriers; 333/333 orphans (book-compose finding).

## Known issues NOT re-litigated (per protocol "What NOT to flag")

`synthesize_bermuda_ledger` non-canonical manifest shape; two `sibling_skills.py` copies; book-qa has no pyproject; `proposed-transitions.jsonl` overwritten per build; `exception_queries` NotImplementedError guard; bermuda manuscript house style; russellian-style deliberately-bad test fixtures; `run_bermuda_counter_claim_gen` hard-coded rivals (the *idempotency* bug H-06 is new, the hard-coded rivals are intentional).

## New this pass (not in prior audit)

All Critical/High items concentrate either in the **two un-ported verifiers** (epi/osmotic — the prior audit didn't single them out, so their drift went unnoticed) or in **paths the prior static-only pass couldn't see by running tests**: the Feynman delta normalization bug (H-07, found by running the scorer), the kg-empty-claims FFI issue (H-03), the stale vendored `_edn_reader` copies (H-08), the codegen injection (H-02, reproduced), and the tools idempotency/coverage gaps. The 2026-05-29 audit explicitly did not run the suite; this pass did, which is why several runtime-only defects surfaced now.
