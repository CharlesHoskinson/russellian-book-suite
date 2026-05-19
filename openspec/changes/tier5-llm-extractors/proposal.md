# Change: tier5-llm-extractors

**Tier:** 5 of 5 (scale + author-facing tier)
**Branch:** `plan/tier5-scale-author`
**Depends on:** Tier 1 (binding-schema), Tier 2
(strict-regex-dialect)

## Why

Every `deflift` form in the framework today is a
hand-authored Python regex pattern (`(?P<v>...)`). For the
osmotic_pressure verifier with ~5 lift patterns this was an
afternoon's work; for a 1000-claim clinical corpus (Phase O)
it is the framework's biggest ergonomic cliff. Authors who
are not regex-fluent — clinicians, biologists, the actual
domain experts the framework exists to serve — bounce off
this surface, and the framework's "general-purpose" framing
collapses to "general-purpose if you can write regex".

A `:backend :llm` lift form, mirroring the
`:backend :z3 / :egg / :cozo` constraint dispatch, closes
that gap. The LLM proposes typed atoms from a claim's
canonical text; the framework type-checks each proposal
against `booklogic-schema.edn`; mismatches surface as a
structured `:llm-lift-rejected` defect rather than the silent
OPAQUE that today's regex failure produces.

## What

- A new `LLMLiftProvider` interface at
  `skills/neurosym-forge/scripts/_llm_lift.py` with
  concrete subclasses `OpenAILift`, `AnthropicLift`,
  `LocalLift` (the last calling a local `ollama` HTTP
  endpoint, default off).
- Provider selection via env var
  `NEUROSYM_LLM_PROVIDER` (`openai` | `anthropic` |
  `local`); per-call timeout via `VERIFIER_LLM_TIMEOUT_MS`
  (default 30000).
- Strict schema validation of every LLM proposal against
  `rules/booklogic-schema.edn`; rejected proposals surface
  `:llm-lift-rejected` defects naming the offending
  predicate.
- A local SQLite cache keyed on `(canonical-text, lift-id)`
  enabled by `NEUROSYM_LLM_CACHE=1`; cache statistics in
  `work/.llm-cache-stats.json`.
- Mixed-backend support — a verifier can have some
  `deflift` forms regex and others `:backend :llm`; both
  produce identical-shape atoms downstream.
- A `SUPPORT_MATRIX.md` row `deflift :backend :llm` flipped
  to `wired (alpha)`; the drift lint asserts the status.
- Stub HTTP responder in tests so the suite runs offline
  by default.

## Capabilities touched

- `llm-lift` — ADD (new capability; LLM-assisted lift
  backend distinct from the existing regex-only path)

## Implementation notes

See `docs/plans/2026-05-19-tier5-scale-author.md`, Phase P.

## Acceptance

- 9 REQ-LLMLIFT IDs ship in `specs/llm-lift/spec.md`.
- `make ci` invokes the LLM provider on a `:backend :llm`
  lift; valid proposals reach the verdict as typed atoms;
  invalid proposals surface as `:llm-lift-rejected`.
- A timeout fixture surfaces `:llm-lift-timeout` and the
  verifier continues with remaining claims.
- `SUPPORT_MATRIX.md` lists `deflift :backend :llm` as
  `wired (alpha)`.
- Unit tests run offline using the stub HTTP responder.
