# Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task. Each task is TDD-shaped: failing test → minimal fix → green → commit. Steps use `- [ ]`.

**Goal:** Fix the verified findings from `docs/audits/2026-06-16-comprehensive-audit/` and close the test-coverage + CI gaps, in leverage order.

**Architecture:** Five sprints. Sprint 1 (verifier chain) is release-blocking for the neurosym gate; Sprints 2–4 are correctness/robustness; Sprint 5 is the coverage + CI track. Each finding maps to one task. Per AGENTS.md: one problem per PR, no AI attribution, never push to main directly, TDD (failing test cites the finding ID).

**Source of truth:** finding IDs (C-00x, H-0x) reference the audit README and per-area files. Run the relevant suite via `cd skills/<skill> && .venv/Scripts/python.exe -m pytest tests -q` (or the verifier's nbb/cargo path).

**Conventions for verifier tasks:** bermuda and adsc-clinical are the reference (fixed) implementations — port FROM them. Verify Rust/cljs via CI (no local cargo/nbb).

---

## Sprint 1 — Verifier chain (release-blocking: C-001..003, H-03/04/08/09)

### Task 1.1: Port the flat-atom bridge to epidemiology + osmotic_pressure (C-001/C-002)

**Files (per verifier, ×2):**
- Modify: `verifiers/<v>/cljs-orchestrator/src/main/<v>/nl_to_fol.cljs` (emit flat `{:kind :expression :id :predicate :subject :value}` — copy bermuda's `legacy-claim->formula`)
- Modify: `verifiers/<v>/cljs-orchestrator/src/main/<v>/phases.cljs:19` (`(pr-str {:version 1 :atoms formulas})`)
- Modify: `verifiers/<v>/cljs-orchestrator/src/main/<v>/ir.cljs` (`Formula = [:or FlatExpression OpaqueMarker]`, copy bermuda)
- Test: `verifiers/<v>/cljs-orchestrator/src/test/<v>/nl_to_fol_test.cljs` (new)

- [ ] **Step 1:** Write `nl_to_fol_test.cljs` asserting `claim->formula` emits a map with `:predicate`/`:subject`/`:value` and NO `:head`/`:args` (mirror `verifiers/adsc-clinical/.../nl_to_fol_test.cljs`).
- [ ] **Step 2:** Run it (CI or `nbb`) — expect FAIL (current output is nested).
- [ ] **Step 3:** Replace `claim->formula` body with bermuda's flat emission; update `phases/verify` to wrap `{:version 1 :atoms …}`; update `ir.cljs Formula`.
- [ ] **Step 4:** Re-run — expect PASS. Add a `phases_test` asserting the payload string contains `:atoms`.
- [ ] **Step 5:** Commit per verifier: `fix(epidemiology): emit flat atoms + :atoms-wrapped verify payload`.

### Task 1.2: Per-verifier cljs CI legs + bridge round-trip test (C-003)

**Files:** Modify `.github/workflows/nightly.yml` (generalize `cljs-bermuda-test` to a matrix over the 4 verifiers); add `verifiers/<v>/.../bridge_test.cljs` (or a Rust integration test that feeds real `translate-corpus` output through `verify_formulas` and asserts a true `:unsat`).

- [ ] Write the matrix job (verifier ∈ {adsc-clinical, bermuda, epidemiology, osmotic_pressure}); write a round-trip test that runs the cljs translator output through the addon. FAIL on epi/osmotic before 1.1, PASS after. Commit.

### Task 1.3: Populate `Verdict.verified` so kg sees real claims (H-03)

**Files:** `verifiers/*/rust-verifier/src/smt.rs` (set `verdict.verified` from the parsed claims that survived solving) + `lib.rs:26`. Test: extend `kg_ingest.rs` / add an FFI-path test asserting `claim_count > 0`.

- [ ] Failing test: assert `ingest_and_summarize` via the lib path returns non-zero `claim_count` for a populated input. Fix: write `verified`. Green. Commit.

### Task 1.4: epidemiology var-name canonicaliser (H-04)

**Files:** Create `verifiers/epidemiology/rust-verifier/src/var_name.rs` (copy adsc); call it in `smt.rs:70-74`. Test: inline `question_prefixed_predicate_canonicalises_to_same_symbol` (copy adsc's).

- [ ] Failing test: `?dose` vs `:dose` contradictory constraints must be `:unsat`. Fix: canonicalise. Green. Commit.

### Task 1.5: De-drift the verifiers (H-08, H-09, Edn::Str, approx=) + sync guard

**Files:** restore `Edn::Str` arm in bermuda/osmotic `smt.rs::bind_atoms`; unify `approx=`/`~=` recognizer in all 4 `booklogic.cljs`; port the `reduce` lift-merge to epi/osmotic; re-sync the 3 stale `_edn_reader.py` from neurosym-forge canonical; add a CI checksum gate over vendored `scripts/*.py` (extend `.checksums.edn` coverage or a new `ci/lint_vendored_sync.py`).

- [ ] One task per item, each with a failing test (e.g. a `/`-Symbol parse test for `_edn_reader`; a duplicate-predicate lift test for the merge). Commit each.
- [ ] **Durable follow-up (design task):** evaluate generating the 4 orchestrators + booklogic compiler from one source instead of vendoring (the root cause of Sprint 1). File as an OpenSpec design.

---

## Sprint 2 — neurosym-forge induction + codegen (H-01, H-02)

### Task 2.1: Wire holdout + tautology into the production CLJS induction path (H-01)

**Files:** `skills/neurosym-forge/.../induce_theory.cljs:407-435` (`-main`) — add holdout-validation + tautology pre-check before persist, routing failures to `rejected`. Mirror `_induction_orchestrator.py:317,342`. Test: a CLI-level test (`test_failure_modes` extended, or a new cljs test) that a memorizing/tautological candidate is rejected via `forge induce`, not via a direct Python `run()`.

- [ ] Failing test (CLI path rejects a tautology). Fix: port the gates into `-main`. Green. Commit.

### Task 2.2: Escape/validate codegen identifiers + id allowlist (H-02)

**Files:** `skills/neurosym-forge/scripts/codegen_axioms.py:1019,1021,1044` (route every `new_const`/`from_str` arg through `_rust_string_literal`/`json.dumps`); `forge_cli.py:233` (validate `constraint_id` against a strict regex). Test: a codegen test feeding an id/string containing `"`/`\`/newline and asserting the emitted Rust is balanced + the injection string does not break out.

- [ ] Failing test (reproduce the injection from the audit). Fix: escape + allowlist. Green. Commit.

### Task 2.3: Bake test asserts codegen output (Important)

**Files:** `skills/neurosym-forge/tests/test_scaffold_bake.py:65` — after `make ci`, read `rust-verifier/src/axioms.rs` and assert the smoke fixture's constraint id + a tracker call landed (better: a known-unsat fixture asserting the emitted defect).

- [ ] Add the assertion. Commit.

---

## Sprint 3 — book-pipeline correctness (H-05, H-07 + book-knowledge/halmos/book-compose)

- [ ] **3.1 (H-05)** book-thesis: reconcile `datalog_consistency.py` detector fields with `claim-record.schema.json` — either add optional `subject`/`value`/`implies` to the schema + populate them at ingest, or read from a typed thesis projection. Failing test: a schema-valid record that SHOULD trip D10 must trip it. Fix. Green.
- [ ] **3.2** book-thesis: rewrite the positive-fire fixtures in `test_datalog_consistency.py` to use schema-valid records; add a regression asserting fixtures pass `validate_claim`.
- [ ] **3.3 (H-07)** feynman-style: match the delta denominators in `score_feynman_delta.py:43-53` (normalize sample over in-vocab tokens, or rebuild the profile over full corpus count). Failing test: a known-answer case (OOV padding must NOT change the delta). Fix. Green.
- [ ] **3.4** book-knowledge: guard `generate_counter_claims.py:51` (`json.loads` + shape assert); add a malformed-LLM test.
- [ ] **3.5** book-knowledge: wire `detect_conflicts` into `conflicts_with` so `contradiction_scan.rq` fires on detector output; test the graph projection.
- [ ] **3.6** halmos: validate dispatcher output shape in `dispatch_halmos_review.py:82` before `rollup`; add a malformed-dispatcher test.
- [ ] **3.7** book-compose: emit `supports:` carriers in `_assemble_manuscript` (or gate `lint_supports` to manuscripts that declare them); test that a real assembled chapter is not 100% D9-orphan.

---

## Sprint 4 — robustness (H-06 + json.loads guards + tools)

- [ ] **4.1 (H-06)** `tools/run_bermuda_counter_claim_gen.py:138` — skip cids whose latest record already has `counter_claim_ids`; test idempotency (two runs → one set).
- [ ] **4.2** Guard unguarded `json.loads(line)` sites by reusing `io_utils.read_jsonl` (skip+warn): `book-qa/sentinel.py:107` + `healer.py`, `book-knowledge/export_symbolic_trace.py`, `book-thesis/datalog_consistency.py:91` + `synthesize_exemplars.py:87`, `build-voice-corpus/manifest.py:33`, `split_bermuda_for_v6.py:68`. One task per site (or a shared helper), each with a corrupt-line test. For the QA gate sites, surface corruption as a synthetic hard-fail ticket.
- [ ] **4.3** `build-voice-corpus/append_to_index.py:29` — seed the per-video id counter from existing entries; test re-index doesn't collide.
- [ ] **4.4** Low-risk cleanups: `book-knowledge/skill_api.py:180` `.get`; `run_competency_queries.py:73` docstring; `iacr-review/consolidate.py:188` median rounding; `lint_ai_staccato.py:200` ReDoS anchor; `score_russell_delta.py` insufficient-text abstain; `strip_internal_ids.py` regex; `process_footnotes.py` missing-def warning.

---

## Sprint 5 — Test-coverage + CI track

**Coverage:**
- [ ] **5.1** book-qa: add `sentinel.main()` / `lint_artifact.main()` exit-code tests (critical-present → 1, clean → 0) — the highest-leverage gap.
- [ ] **5.2** tools: add a `tools/` entry to `ci/compute_matrix.py` (or a dedicated CI job) running `tools/` tests; write round-trip + idempotency tests for the 4 live canonical-artifact writers (`synthesize_bermuda_ledger`, `split_bermuda_for_v6`, `run_bermuda_counter_claim_gen`, `process_footnotes`).
- [ ] **5.3** verifiers: the per-verifier cljs CI matrix + bridge round-trip test (delivered in Task 1.2 — verify it's wired).
- [ ] **5.4** feynman: the known-answer delta test (delivered in 3.3).
- [ ] **5.5** neurosym: the codegen-output bake assertion (3.3) + a toolchain-free structural validation of generated Rust/CLJS (tree-sitter parse / per-constraint `assert_and_track` count).

**CI hardening:**
- [ ] **5.6** Add a nightly Clojure CVE-scan job (clj-watson/clj-holmes) over the 4 `deps.edn`; pin coords.
- [ ] **5.7** Add a nightly `macos-15` `nix flake check` leg (or narrow `supportedSystems` darwin + document best-effort).
- [ ] **5.8** Install `shellcheck` in the actionlint job so the `SC2086` pragmas are honored.
- [ ] **5.9** `ci/compute_matrix.py:114` — fail closed on a per-entry empty `os` list; test.
- [ ] **5.10** `ci/lint_no_direct_http.py` — also flag `__import__`/`importlib.import_module` of forbidden modules (or document static-only).
- [ ] **5.11** Add the vendored-`_edn_reader` checksum gate (delivered in 1.5 — verify).

**Docs:**
- [ ] **5.12** `docs/operations/ci-platforms.md:14` → `macos-15`.
- [ ] **5.13** README/AGENTS/CLAUDE: add `triadic-voice` to the tree + enumerations + install loops; reconcile the skill count (10 vs 9) and paragraph-weaver's tier; add `nix/`+`scripts/` to the layout tree; note `tools/build-voice-corpus` as a built project; glob `skills/*` in the install/test loops.

---

## Self-review

- Spec coverage: every Critical (C-001..003 → 1.1/1.2), every High (H-01..09 → 2.1/2.2, 1.1/1.3/1.4/1.5, 3.1/3.3), every Medium/Low (Sprints 3–5) maps to a task.
- The coverage + CI track (Sprint 5) directly addresses "improve test coverage and CI."
- No placeholders: each task names files, the failing test's intent, and the fix source (port-from-bermuda for verifiers).
