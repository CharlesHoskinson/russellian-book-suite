# Design: tier5-llm-extractors

## Provider interface

A single abstract base class at
`skills/neurosym-forge/scripts/_llm_lift.py`:

```python
class LLMLiftProvider:
    """Abstract LLM lift backend.

    Subclasses implement `extract_atoms(canonical_text,
    emit_template) -> list[dict]` and produce candidate
    typed-atom proposals. The framework schema-validates each
    proposal before insertion."""

    name: str  # "openai" | "anthropic" | "local"

    def extract_atoms(
        self,
        canonical_text: str,
        emit_template: dict,
        timeout_ms: int,
    ) -> list[dict]: ...
```

Concrete subclasses:

- `OpenAILift` — `OPENAI_API_KEY`, chat completions, JSON mode
- `AnthropicLift` — `ANTHROPIC_API_KEY`, messages API, tool
  use forcing the structured proposal shape
- `LocalLift` — `OLLAMA_HOST` (default
  `http://localhost:11434`), POST to `/api/generate` with
  `format=json`

## Prompt template

Zero-shot. The lift's `:emit` template carries the expected
atom shape; the prompt asks the LLM to produce that shape
from the claim text:

```
You are extracting structured atoms from a claim.

Claim text: "{canonical_text}"

The atom must match this schema:
{emit_template}

Respond with a JSON array of one or more atom objects. Use
only predicate names that appear in the schema. Use only
argument sorts the schema declares. If you cannot extract a
matching atom, respond with [].
```

Few-shot is a follow-up; the alpha is zero-shot to keep the
prompt minimal and the failure modes legible.

## Schema validation

Every proposal flows through
`_llm_lift.validate_proposal(atom, schema)` which checks:

1. The predicate name exists in `booklogic-schema.edn`'s
   predicate registry.
2. Each argument matches the declared sort
   (`:int` parses as int, `:real` as float, `:keyword` as
   keyword, etc.).
3. The return value's sort matches the predicate's declared
   return.

Failures emit a structured
`{:phase :llm-lift :reason :llm-lift-rejected :predicate
:p-value :offending-atom {...} :provider :openai}` defect.
The build log carries the raw LLM response for debugging;
the verdict surface carries the validated shape only.

## Cache shape

When `NEUROSYM_LLM_CACHE=1`:

```sql
CREATE TABLE llm_lift_cache (
    canonical_text TEXT NOT NULL,
    lift_id        TEXT NOT NULL,
    provider       TEXT NOT NULL,
    proposal_json  TEXT NOT NULL,
    created_at     INTEGER NOT NULL,
    PRIMARY KEY (canonical_text, lift_id, provider)
);
```

Database path: `work/.llm-cache.sqlite`. Stats sidecar
`work/.llm-cache-stats.json` records hits, misses, average
proposal size, and provider mix per run. Hits are
deterministic by construction; misses log the network
latency.

## Timeout handling

`VERIFIER_LLM_TIMEOUT_MS` (default 30000) wraps each
provider call via `concurrent.futures.ThreadPoolExecutor` +
`future.result(timeout=...)`. On timeout, the framework
emits `:llm-lift-timeout` on the verdict's `:warnings` list
and continues with the next claim. The partial verdict is
valid — `:status` reflects only the claims that completed.

## Mixed-backend support

A verifier can declare:

```edn
(deflift L001-p-value-regex
  :backend :regex
  :pattern "p\\s*<\\s*(?P<v>0\\.\\d+)"
  :emit ...)

(deflift L002-narrative-extraction
  :backend :llm
  :emit {:predicate :primary-endpoint
         :args [{:sort :trial}]
         :return :keyword})
```

The downstream constraint surface receives identical-shape
atoms from both lifts. The verdict's defect-class taxonomy
does not branch on lift backend; a constraint over
`:primary-endpoint` does not care whether the atom came from
regex or LLM. This is the contract that makes incremental
adoption possible — start regex, migrate the pattern-resistant
claims to `:backend :llm` one lift at a time.

## CI safety: the stub responder pattern

Tests under `tests/test_llm_lift_*.py` start a tiny in-process
HTTP server (`http.server.HTTPServer`) on a random port and
inject `LLMLiftProvider`'s base URL to point at it. The
responder returns pre-canned JSON proposals from a fixtures
directory (`tests/fixtures/llm-responses/*.json`). No
network egress; no API key required; deterministic.

`NEUROSYM_LLM_PROVIDER=stub` selects the stub directly;
production providers are exercised only by an opt-in
`make test-llm-online` target.

## Security: API key handling

API keys are read from environment variables only —
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`. The framework
explicitly refuses to read keys from any file under `rules/`
or `work/`, and the build log scrubs any header value
matching `(?i)(authorization|api-key)`. A unit test
(`test_llm_lift_security.py::test_no_api_key_in_build_log`)
asserts the scrub.

## SUPPORT_MATRIX update

One row addition:

```
| `deflift :backend :regex`     | wired         | `predicates.edn`    | n/a    | wired              |
| `deflift :backend :llm`       | wired (alpha) | `_llm_lift.py`      | LLM    | wired (alpha)      |
```

The `wired (alpha)` legend entry is introduced:

> **wired (alpha)** — Full end-to-end path is implemented and
> CI-tested against a stub responder. Real-provider behaviour
> depends on the chosen model; users should expect
> proposal-quality variance and exercise the cache + schema
> validation as belt-and-braces. Promoted to `wired` once
> Phase Q's eval bench confirms detection rates within 5
> percentage points of the regex baseline.

## Why not bundle into Phase Q (semantic retrieval)?

Phase Q's encoder embeds text. Phase P's LLM proposes atoms.
The two share zero infrastructure: Phase P is a JSON-shape
contract, Phase Q is a vector index. Bundling them would mix
concerns and force one to wait on the other.
