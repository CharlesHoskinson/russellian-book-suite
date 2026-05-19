# Tasks: tier5-llm-extractors

See `docs/plans/2026-05-19-tier5-scale-author.md` Phase P for full
TDD steps. Task numbers correspond 1:1.

## Phase P.1 — Provider interface + stub responder

- [ ] P1.1: Author `skills/neurosym-forge/scripts/_llm_lift.py` with abstract `LLMLiftProvider`, concrete `OpenAILift`, `AnthropicLift`, `LocalLift`, and a `StubLift` selected by `NEUROSYM_LLM_PROVIDER=stub`. (REQ-LLMLIFT-041)
- [ ] P1.2: Author `tests/conftest.py::stub_llm_server` fixture starting a `http.server.HTTPServer` on a random port; responses driven by `tests/fixtures/llm-responses/*.json`. (REQ-LLMLIFT-048)
- [ ] P1.3: Unit test each provider class against the stub responder, asserting request shape (URL, headers, body) and response parsing. (REQ-LLMLIFT-048)

## Phase P.2 — Schema validation + rejection defect

- [ ] P2.1: Author `_llm_lift.validate_proposal(atom, schema)` checking predicate name, arg sorts, return sort. (REQ-LLMLIFT-042)
- [ ] P2.2: On validation failure, emit `:llm-lift-rejected` defect on the verdict naming the offending predicate; the build log retains the raw LLM response. (REQ-LLMLIFT-043)
- [ ] P2.3: Test `test_llm_lift_rejection.py::rejection_carries_predicate_name_and_does_not_corrupt_verdict`. (REQ-LLMLIFT-043)

## Phase P.3 — Codegen dispatch on :backend :llm

- [ ] P3.1: Extend `codegen_axioms.py` to recognise `:backend :llm` on `deflift` forms, routing through `_llm_lift.extract_atoms`. (REQ-LLMLIFT-040)
- [ ] P3.2: Mixed-backend test: a verifier with one `:regex` lift and one `:llm` lift produces identical-shape atoms; downstream constraints fire regardless of lift origin. (REQ-LLMLIFT-046)

## Phase P.4 — Timeout + cache

- [ ] P4.1: Wrap each provider call in `ThreadPoolExecutor.future.result(timeout=VERIFIER_LLM_TIMEOUT_MS/1000)`. On timeout emit `:llm-lift-timeout` warning; continue with remaining claims. (REQ-LLMLIFT-044)
- [ ] P4.2: SQLite cache at `work/.llm-cache.sqlite` keyed on `(canonical_text, lift_id, provider)`. Stats sidecar `work/.llm-cache-stats.json`. Enabled by `NEUROSYM_LLM_CACHE=1`. (REQ-LLMLIFT-045)
- [ ] P4.3: Test cache round-trip — first call hits the network (stub), second call hits the cache, stats sidecar increments. (REQ-LLMLIFT-045)

## Phase P.5 — SUPPORT_MATRIX + security + commit

- [ ] P5.1: Update `SUPPORT_MATRIX.md`: add `deflift :backend :llm | wired (alpha)` row; add the `wired (alpha)` legend entry. Drift lint asserts the new state. (REQ-LLMLIFT-047)
- [ ] P5.2: Security test: `test_llm_lift_security.py::test_no_api_key_in_build_log` asserts the scrub on `Authorization`/`api-key` headers. (REQ-LLMLIFT-048)
- [ ] P5.3: Commit verifier-side changes and provider-side changes once P1-P5 are green.
