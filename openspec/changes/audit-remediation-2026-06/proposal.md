# Change: audit-remediation-2026-06

**Branch:** `audit/2026-06-16-comprehensive` (audit) → remediation PRs per sprint
**Source:** `docs/audits/2026-06-16-comprehensive-audit/` (3 critical, 9 high, ~21 medium, ~20 low)
**Plan:** `docs/superpowers/plans/2026-06-16-audit-remediation.md`

## Why

The 2026-06-16 comprehensive audit found the Python book pipeline healthy and releasable, but the **neurosymbolic verifier layer is not trustworthy**: the prior audit's #1 critical (the cljs→Rust verify contract) was fixed in `bermuda`/`adsc-clinical` but never ported to `epidemiology`/`osmotic_pressure`, so those two verify nothing — and CI runs cljs tests for `bermuda` only, so the regression is invisible. The root cause is structural: four hand-maintained verifier copies that drift, producing five more high/medium bugs. Separately, the neurosym-forge induction gates (holdout, tautology) live only on the test-only Python path, the codegen string-handling is injection-shaped, and several test/CI gaps let runtime defects ship.

## What

Five sprints (full task list in the plan; REQ deltas below):

1. **Verifier chain** — port the flat-atom bridge to epi/osmotic; add per-verifier cljs tests + CI legs; populate `Verdict.verified` for kg; add epidemiology's var-name canonicaliser; de-drift (`Edn::Str` arm, `approx=` recognizer, lift-merge, stale `_edn_reader`) + a vendored-sync CI gate; design a single-source-of-truth follow-up.
2. **neurosym-forge** — wire holdout + tautology into the production CLJS `induce -main`; escape/validate codegen identifiers + id allowlist; assert codegen output in the bake test.
3. **Book-pipeline correctness** — reconcile book-thesis datalog detectors with the claim schema; fix the Feynman delta normalization; guard LLM-output parsing (book-knowledge, halmos); wire detect_conflicts → contradiction gate; emit supports carriers.
4. **Robustness** — idempotent counter-claim gen; guard all unguarded `json.loads(line)` ledger reads; low-risk cleanups.
5. **Test-coverage + CI** — gate exit-code tests; a `tools/` CI entry + canonical-writer tests; Clojure CVE scan; darwin flake check; shellcheck; compute_matrix empty-os guard; doc reconciliation (triadic-voice, skill count, ci-platforms).

## Impact

- **Capabilities affected:** verifier-bridge (VRF), neurosym-induction (NSI), book-thesis-consistency (BTC), style-delta (STY), qa-gate (QAG), ci-coverage (CIC).
- **Behavior change:** epidemiology/osmotic_pressure verifiers begin producing real verdicts; the neurosym gate becomes trustworthy across all four verifiers. No change to the Python book-pipeline release semantics (already correct).
- **Risk:** Sprint 1 touches generated Rust/cljs that can only be verified in CI; land per-verifier with the new cljs CI legs green before merge.

## Requirements (deltas)

- **REQ-VRF-001** The cljs `verify` phase SHALL emit a top-level `{:version N :atoms [...]}` map of flat `{:kind :expression :id :predicate :subject :value}` atoms for every verifier, matching the Rust `parse_formulas`/`bind_atoms` contract.
- **REQ-VRF-002** Each verifier SHALL have cljs tests for `nl_to_fol` + `phases/verify` and a bridge round-trip test, and CI SHALL run the cljs suite for every verifier (not bermuda only).
- **REQ-VRF-003** The kg path SHALL receive the solved claim set (`Verdict.verified` populated), not an empty vector.
- **REQ-VRF-004** Vendored `scripts/*.py` (incl. `_edn_reader.py`) SHALL be checksum-verified against their canonical source in CI.
- **REQ-NSI-001** The production `forge induce` path SHALL apply the holdout (memorization) and tautology gates before persisting a candidate.
- **REQ-NSI-002** Generated Rust identifiers and string literals SHALL be escaped/validated at the codegen boundary; constraint ids SHALL be validated against an allowlist.
- **REQ-BTC-001** The book-thesis contradiction/invariant detectors SHALL operate on schema-valid claim fields (or an explicitly-typed projection), and their positive-fire tests SHALL use schema-valid records.
- **REQ-STY-001** The Feynman delta SHALL normalize profile and sample over matched denominators and SHALL have a known-answer test.
- **REQ-QAG-001** The release-gate entry points (`sentinel.main`, `lint_artifact.main`) SHALL have exit-code tests; internal QA-artifact reads SHALL tolerate a corrupt file by surfacing a synthetic hard-fail.
- **REQ-CIC-001** `tools/` SHALL run in CI; the live canonical-artifact writers SHALL have round-trip + idempotency tests; Clojure deps SHALL be CVE-scanned; declared darwin systems SHALL be flake-checked or documented best-effort.
