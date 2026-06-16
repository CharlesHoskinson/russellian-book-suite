# Tasks — audit-remediation-2026-06

Detailed TDD steps in `docs/superpowers/plans/2026-06-16-audit-remediation.md`. Each task: failing test citing the REQ-ID → minimal fix → green → commit. One problem per PR.

## Sprint 1 — verifier chain (release-blocking)

> **Reconciled 2026-06-16** against `origin/main` @ `c695de9`. Sprint 1 landed via
> PRs #225/#227/#228/#229; boxes were not updated at the time. T1.2 left open to
> verify the per-verifier cljs round-trip test (coverage was expanded in #225).
> T1.6 (design follow-up) is still open and carries into a future sprint.

- [x] T1.1 Port flat-atom `nl_to_fol` + `{:atoms}` verify payload + `ir.cljs Formula` to epidemiology, osmotic_pressure (REQ-VRF-001) [C-001, C-002] — #227
- [ ] T1.2 Per-verifier cljs CI matrix + bridge round-trip test (REQ-VRF-002) [C-003] — coverage expanded in #225; **verify** the bridge round-trip test is wired
- [x] T1.3 Populate `Verdict.verified` for the kg path (REQ-VRF-003) [H-03] — #228
- [x] T1.4 epidemiology `var_name.rs` canonicaliser (REQ-VRF-001) [H-04] — #228
- [x] T1.5 De-drift: `Edn::Str` arm, `approx=`/`~=` recognizer, `reduce` lift-merge, re-sync 3 stale `_edn_reader.py` + checksum gate (REQ-VRF-004) [H-08, H-09] — #229 + `ci/test_vendored_sync.py`
- [ ] T1.6 Design: single source of truth for the 4 orchestrators (root-cause follow-up) — **open**

## Sprint 2 — neurosym-forge
> **Next sprint.** Sequenced with the v0.6 predicate-UF soundness centerpiece in
> `docs/superpowers/plans/2026-06-16-sprint2-codegen-soundness.md`. T2.2 (H-02)
> shares `codegen_axioms.py` with the v0.6 work — land the escaping inside the new
> `apply` emission.
- [ ] T2.1 Holdout + tautology gates into CLJS `induce_theory.cljs -main` (REQ-NSI-001) [H-01]
- [ ] T2.2 Escape/validate codegen identifiers + constraint-id allowlist (REQ-NSI-002) [H-02]
- [ ] T2.3 Bake test asserts codegen output [neurosym Important]

## Sprint 3 — book-pipeline correctness
- [ ] T3.1 book-thesis detectors ↔ claim schema (REQ-BTC-001) [H-05]
- [ ] T3.2 Schema-valid datalog test fixtures (REQ-BTC-001)
- [ ] T3.3 Feynman delta denominator fix + known-answer test (REQ-STY-001) [H-07]
- [ ] T3.4 book-knowledge `generate_counter_claims` LLM guard
- [ ] T3.5 detect_conflicts → `conflicts_with` → contradiction gate
- [ ] T3.6 halmos dispatcher-output shape validation
- [ ] T3.7 book-compose supports carriers (or gate lint_supports)

## Sprint 4 — robustness
- [ ] T4.1 Idempotent `run_bermuda_counter_claim_gen` (REQ-QAG-001 adjacency) [H-06]
- [ ] T4.2 Guard all unguarded `json.loads(line)` ledger reads; QA-gate sites surface synthetic hard-fail (REQ-QAG-001)
- [ ] T4.3 `append_to_index` id-counter seeding
- [ ] T4.4 Low-risk cleanups (skill_api.get, docstring, median, ReDoS, abstain, regex, footnote warning)

## Sprint 5 — coverage + CI
- [ ] T5.1 Gate exit-code tests (REQ-QAG-001)
- [ ] T5.2 `tools/` CI entry + canonical-writer round-trip/idempotency tests (REQ-CIC-001)
- [ ] T5.3 Verify per-verifier cljs CI matrix (from T1.2)
- [ ] T5.4 Verify Feynman known-answer test (from T3.3)
- [ ] T5.5 Toolchain-free structural validation of generated Rust/cljs
- [ ] T5.6 Clojure CVE-scan nightly job (REQ-CIC-001)
- [ ] T5.7 darwin `nix flake check` leg or documented best-effort (REQ-CIC-001)
- [ ] T5.8 shellcheck in actionlint job
- [ ] T5.9 compute_matrix per-entry empty-os guard
- [ ] T5.10 lint_no_direct_http dynamic-import flag/doc
- [ ] T5.11 Verify vendored-sync checksum gate (from T1.5)
- [ ] T5.12 ci-platforms.md macos-15
- [ ] T5.13 README/AGENTS/CLAUDE: triadic-voice + skill count + layout tree + install globs
