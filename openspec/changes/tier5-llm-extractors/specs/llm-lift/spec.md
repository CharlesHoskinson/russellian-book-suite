# Capability delta: llm-lift — change: tier5-llm-extractors

This change introduces a new capability `llm-lift`, the
framework's LLM-assisted lift backend. Today every
`deflift` form is hand-authored Python regex; this change
adds a `:backend :llm` form that proposes typed atoms via a
provider-abstracted LLM call, schema-validated against
`rules/booklogic-schema.edn` before insertion.

## ADD

### REQ-LLMLIFT-040 — Optional feature

WHERE a `deflift` form declares `:backend :llm`, the
framework SHALL invoke an LLM via the configured provider
(`NEUROSYM_LLM_PROVIDER` env var: `openai` | `anthropic` |
`local` | `stub`) with the claim's canonical text and the
lift's `:emit` template, expecting a structured atom
proposal as a JSON array of atom objects.

**Rationale:** Hand-authored regex is the framework's
biggest ergonomic cliff for real-corpus authors. A
declarative `:backend :llm` form mirrors the existing
`:backend :z3/:egg/:cozo` dispatch and lets authors mix
backends per-lift.
**Tested by:** `tests/test_llm_lift_backend.py::test_backend_llm_invokes_configured_provider` (added in P3.1).

### REQ-LLMLIFT-041 — Ubiquitous

The LLM provider interface SHALL be defined at
`skills/neurosym-forge/scripts/_llm_lift.py` with a
`class LLMLiftProvider` abstract base and concrete
subclasses `OpenAILift`, `AnthropicLift`, `LocalLift` (the
last calling a local model via `ollama` HTTP, default off).
A `StubLift` subclass SHALL be available for offline tests.

**Rationale:** A single interface lets the codegen dispatch
loop stay provider-agnostic; subclasses encapsulate the
request shape and response parsing per vendor.
**Tested by:** `tests/test_llm_lift_providers.py::test_each_provider_class_handles_stub_request_response` (added in P1.1).

### REQ-LLMLIFT-042 — Ubiquitous

Each proposed atom SHALL be validated against
`rules/booklogic-schema.edn` BEFORE insertion into the
claims registry; the predicate name, argument sorts, and
return sort SHALL all match the declared schema.

**Rationale:** An LLM proposal that bypasses schema
validation corrupts the downstream constraint surface
silently; the verdict appears clean while the underlying
atoms are mis-typed. Strict validation forces every proposal
through the same type gate as a regex-extracted atom.
**Tested by:** `tests/test_llm_lift_validation.py::test_schema_mismatch_blocks_insertion` (added in P2.1).

### REQ-LLMLIFT-043 — Unwanted behaviour

IF the LLM proposal fails schema validation, the framework
SHALL emit a `:llm-lift-rejected` defect on the verdict (NOT
the OPAQUE silent-drop today's regex failures produce)
naming the offending predicate. The build log SHALL include
the LLM's raw response for debugging; the verdict surface
SHALL include the validated shape only.

**Rationale:** Today a regex that fails to match emits no
defect — the claim is silently OPAQUE. For LLM lifts this
behaviour is unsafe: a hallucinated predicate name should
surface as a structured defect, not vanish.
**Tested by:** `tests/test_llm_lift_rejection.py::test_rejected_proposal_surfaces_defect_with_predicate_name` (added in P2.2).

### REQ-LLMLIFT-044 — Unwanted behaviour

IF the LLM call exceeds `VERIFIER_LLM_TIMEOUT_MS` (default
30000), the framework SHALL emit a `:llm-lift-timeout`
warning on the verdict's `:warnings` list and SHALL continue
evaluating remaining claims. The partial verdict SHALL be
valid; `:status` SHALL reflect only the claims that
completed.

**Rationale:** A hung provider call must not block the rest
of the verifier. Mirrors `VERIFIER_DATALOG_TIMEOUT_MS` from
Phase H; one slow lift SHALL NOT wedge the run.
**Tested by:** `tests/test_llm_lift_timeout.py::test_slow_provider_emits_timeout_and_continues` (added in P4.1).

### REQ-LLMLIFT-045 — Optional feature

WHERE `NEUROSYM_LLM_CACHE=1` is set, identical
`(canonical-text, lift-id, provider)` tuples SHALL hit a
local SQLite cache at `work/.llm-cache.sqlite`; cache hits
SHALL be free and deterministic; cache misses SHALL be
recorded in a sidecar `work/.llm-cache-stats.json` with hit
count, miss count, average proposal size, and provider mix.

**Rationale:** Cost discipline — LLM calls in CI rack up
real charges. The cache makes re-runs free and the
deterministic-by-key shape lets tests rely on cache hits.
**Tested by:** `tests/test_llm_lift_cache.py::test_cache_hit_skips_provider_and_increments_stats` (added in P4.2).

### REQ-LLMLIFT-046 — Optional feature

WHERE a verifier mixes lift backends — some `deflift` forms
`:backend :regex`, others `:backend :llm` — both SHALL
produce identical-shape atoms; downstream constraints SHALL
NOT branch on lift origin and the verdict's defect-class
taxonomy SHALL NOT distinguish atoms by lift backend.

**Rationale:** This is the contract that makes incremental
adoption possible — an author can start with regex lifts and
migrate the pattern-resistant ones to `:backend :llm` one at
a time without rewriting constraints.
**Tested by:** `tests/test_llm_lift_mixed.py::test_constraint_fires_on_atoms_from_both_backends` (added in P3.2).

### REQ-LLMLIFT-047 — Ubiquitous

`skills/neurosym-forge/SUPPORT_MATRIX.md` SHALL be updated
to add a `deflift :backend :llm | wired (alpha)` row and a
`wired (alpha)` legend entry. The drift lint
`tests/test_support_matrix.py` SHALL assert the new row's
status matches the codegen dispatch state.

**Rationale:** Without the matrix update, the framework
documents a stub status for code that is now live; the lint
catches the drift, as it did for `:cozo` and `:egg` in
Tier 3.
**Tested by:** `tests/test_support_matrix.py::test_matrix_matches_codegen_after_llm_lift_promotion` (added in P5.1).

### REQ-LLMLIFT-048 — Ubiquitous

A unit-test suite SHALL exercise each provider class against
a stub HTTP responder; tests SHALL run offline by default.
The stub responder SHALL be selected by
`NEUROSYM_LLM_PROVIDER=stub`; production-provider tests
SHALL be opt-in via `make test-llm-online`. The build log
SHALL scrub `Authorization` and `api-key` header values.

**Rationale:** CI cannot rely on live API keys or network
egress; the stub responder gives every provider class a
deterministic, offline test path. The header scrub is a
security gate — leaked API keys in build logs are the most
common LLM-tooling incident class.
**Tested by:** `tests/test_llm_lift_offline.py::test_full_suite_passes_without_network` and `tests/test_llm_lift_security.py::test_no_api_key_in_build_log` (added in P1.3 and P5.2).
