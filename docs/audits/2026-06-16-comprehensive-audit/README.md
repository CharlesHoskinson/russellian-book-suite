# Comprehensive end-to-end audit — 2026-06-16

**Reviewed commit:** `86c478ba9533f2bc975e8541673245a7f6e8c188` (branch `audit/2026-06-16-comprehensive`, off `main`)
**Method:** graphify-partitioned hybrid matrix — 11 subsystem/dimension agents across the `codex-review-protocol` 7 dimensions + verifier-soundness / CI / coverage extensions; suites actually run per subsystem; criticals adversarially cross-confirmed. Graph: `graphify-out/` (16,264 nodes, 1,394 communities).
**Baseline tests (run this pass, not just static):** book-knowledge 174✓ · book-compose 133✓ · book-thesis 33✓ · paragraph-weaver 49✓ · russellian-style 185✓ · feynman-style 45✓ · halmos 29✓ · book-qa 68✓ · review-conductor 55✓ · iacr-review 6✓ · neurosym-forge 517✓ · build-voice-corpus 58✓. Ruff clean; `ci/` green; actionlint clean.

## Executive summary

The **Python book-pipeline is healthy and releasable** — every prior-audit CRITICAL in the Python skills (the book-qa release-gate routing, the dedup/severity defects, the missing-gating false-pass) is **fixed and regression-tested**, and the CI overhaul closed the prior branch-protection merge-wedge. The defects that remain concentrate in the **neurosymbolic verifier layer**, where the prior audit's #1 critical was only **half-remediated**: the cljs→Rust contract fix landed in `bermuda` and `adsc-clinical` but was never ported to `epidemiology` and `osmotic_pressure` (the latter is the showcase verifier), so those two verify nothing today — and because CI runs cljs tests for `bermuda` only, the regression is invisible. The root cause is structural: the four verifiers are hand-maintained copies that drift, and the same divergence produced four more high/medium bugs.

**Severity counts (confirmed this pass):** 3 Critical · 9 High · ~21 Medium · ~20 Low. **Releasable state:** the Python book pipeline is releasable; the **optional neurosym-forge satisfiability gate is NOT trustworthy** on epidemiology/osmotic_pressure and should be treated as non-gating until the bridge is repaired.

## Critical findings

| ID | Location | Finding |
|---|---|---|
| **C-001** | `verifiers/osmotic_pressure/cljs-orchestrator/.../phases.cljs:19` + `nl_to_fol.cljs:11-34` | The showcase verifier's `verify` sends a bare `(pr-str formulas)` (no `{:atoms …}` wrapper) of nested `{:head/:args}` formula trees; Rust `parse_formulas` returns `Err("missing or non-vector :atoms")` and `bind_atoms` skips every nested atom → trivially `:sat`. **Verifies nothing.** Triple-confirmed (Rust agent, cljs agent, direct grep: 5 `:head`, 0 `:predicate`). |
| **C-002** | `verifiers/epidemiology/cljs-orchestrator/.../phases.cljs:19` + `nl_to_fol.cljs:11-34` | Identical dead bridge on epidemiology. Same bare-vector payload + nested trees. The C-1/C-2 fix that landed in bermuda/adsc was never ported here. |
| **C-003** | `verifiers/{epidemiology,osmotic_pressure}/cljs-orchestrator` + `.github/workflows/nightly.yml` (`cljs-bermuda-test`) | No `nl_to_fol`/`phases`/bridge cljs tests exist for epi/osmotic, and CI runs cljs tests for **bermuda only**; the Rust integration tests feed correctly-shaped `{:atoms …}` EDN directly, bypassing the broken cljs producer → false green. This coverage gap is *why* C-001/C-002 shipped. |

## High findings

| ID | Location | Finding |
|---|---|---|
| H-01 | `skills/neurosym-forge/.../induce_theory.cljs:407-435` | `forge induce` runs the CLJS `-main`, which has **no holdout (memorization) gate and no tautology gate**. The prior-audit fixes were applied to the test-only Python orchestrator (`_induction_orchestrator.py`); `_induction_validator.is_trivial_tautology` has zero production callers. Memorizing/trivial candidates are persisted to `candidates.edn`. |
| H-02 | `skills/neurosym-forge/scripts/codegen_axioms.py:1019,1021,1044` | Author/ledger-controlled ids, predicate/subject names, and string literals are interpolated into generated `axioms.rs` via bare f-strings (`new_const("{cid}")`, `from_str("{name}")`) with absent/partial escaping → **reproduced Rust code injection** / silent miscompile. The correct helper `_rust_string_literal` exists but these paths bypass it; `forge add-constraint` applies no id allowlist. |
| H-03 | all 4 `verifiers/*/rust-verifier/src/lib.rs:26` + `kg.rs` | `kg::ingest_and_summarize(&v.verified)` is called, but `smt::check_all` never populates `Verdict.verified` (zero writers). Through the napi FFI the kg layer always gets 0 claims → bermuda's contradiction query can never fire; `claim_count` always 0. kg is inert in production. |
| H-04 | `verifiers/epidemiology/rust-verifier/src/smt.rs:70-74` | epidemiology has no var-name canonicaliser; it strips `:` but not `?`, so `?dose` and `:dose` map to different Z3 symbols → contradictory constraints come out `:sat` (false). adsc/bermuda/osmotic call `canonical_var_name`; epidemiology never adopted it. |
| H-05 | `skills/book-thesis/scripts/datalog_consistency.py:147-156` + `rules/consistency.dl` | The D10 transitive-contradiction and D11 invariant detectors read `claim_value`/`implies`, which the canonical `claim-record.schema.json` (`additionalProperties:false`) forbids. Verified: bermuda's 50-record ledger has 0 occurrences. The detectors are **inert on any real ledger** (only `declared_conflict` works). Carry-forward; the invariant-compilation work made the rule fireable-in-principle but didn't close the field mismatch. |
| H-06 | `tools/run_bermuda_counter_claim_gen.py:138-141` | Non-idempotent: re-running calls `generate_for_claim` per rival with no skip-if-present guard, so it **doubles the canonical counter-claim ledger**. The generic path (`generate_for_all_load_bearing`) has the guard; this one-shot omits it. The workspace already has counter-claims, so a re-run is the realistic hazard. |
| H-07 | `skills/feynman-style/scripts/score_feynman_delta.py:43-53` + `build_delta_profile.py:30` | Asymmetric frequency normalization: the profile divides by the top-500 subtotal; the scorer divides the sample by ALL tokens (incl. OOV). The two distributions use different denominators → the delta tracks document OOV-rate, not Feynman-similarity (reproduced: 10× inflation under 50% OOV padding). The Russell scorer is the correct template. |
| H-08 | `verifiers/{bermuda,epidemiology,osmotic_pressure}/scripts/_edn_reader.py` | 5 vendored copies of `_edn_reader.py`; 3 are stale (byte-identical at 291 lines) and miss a 4-line bare-`/` Symbol fix the canonical 295-line copy has → they mis-parse a `/` Symbol. Vendoring is intentional, but there is **no checksum/CI sync guard** (`.checksums.edn` covers only `rules/*.edn`). |
| H-09 | `verifiers/{epidemiology,osmotic_pressure}/.../booklogic.cljs:469` | `emit-predicates-edn-string` uses `(into {} …)`, silently dropping all but the last lift when two lifts target the same predicate; bermuda/adsc use a merging `reduce`. Latent (epi/osmotic lifts.edn currently have no duplicates) but a foot-gun; bermuda's lifts.edn already relies on the merge (5 duplicate groups). |

Medium and Low findings (~41 total) are itemized in the per-area files below.

## Per-area detail

- [`findings-verifiers.md`](findings-verifiers.md) — the verifier/cljs deep dive (C-001..003, H-01..04, H-08..09, the 4-way drift table)
- [`findings-skills-tools.md`](findings-skills-tools.md) — book-knowledge, composition, style/voice, review/QA, delta-scoring, tools (correctness/tests/security/docs/schema)
- [`findings-cicd.md`](findings-cicd.md) — CI/Nix/build (mostly reconciliation wins + 3 medium doc/coverage gaps)
- [`reconciliation.md`](reconciliation.md) — every 2026-05-29 finding tagged fixed / still-open / new
- [`coverage-map.md`](coverage-map.md) — graphify community coverage + measured test-coverage gaps
- [`baseline.md`](baseline.md) — commit, scope, method

## Next steps (by leverage)

1. **Port the cljs→Rust bridge fix to epidemiology + osmotic_pressure** (C-001/C-002) and **add per-verifier cljs tests + CI legs** (C-003) so it can't silently regress again.
2. **Wire holdout + tautology into the production CLJS induction path** (H-01) and **escape/validate codegen identifiers** (H-02).
3. **De-duplicate the verifiers** — the durable fix for C-001/H-03/H-04/H-08/H-09 is a single source of truth (shared codegen / sync-checked vendoring) instead of four drifting copies.
4. **Fix the Feynman delta normalization** (H-07) with a known-answer test; **reconcile book-thesis detector fields with the claim schema** (H-05).
5. **Close the test/CI coverage gaps**: tools/ runs in no CI; epi/osmotic cljs untested; gate exit-codes untested; Clojure deps unscanned — see the remediation plan `docs/superpowers/plans/2026-06-16-audit-remediation.md`.
