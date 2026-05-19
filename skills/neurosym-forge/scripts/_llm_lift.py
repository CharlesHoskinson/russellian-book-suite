"""REQ-LLMLIFT-040..043, 048: LLM-backed lift providers + schema validation.

Four concrete implementations:
  OpenAILift    — uses openai SDK; needs OPENAI_API_KEY
  AnthropicLift — uses anthropic SDK; needs ANTHROPIC_API_KEY
  LocalLift     — POSTs to a local Ollama HTTP endpoint at OLLAMA_URL
                  (default http://localhost:11434)
  StubLift      — returns a canned JSON; offline, deterministic, used in CI

The provider class is selected by NEUROSYM_LLM_PROVIDER env var. Default
in test mode: 'stub'. Default in production: 'openai'.

Schema validation: every proposed atom MUST pass `validate_proposal`
before insertion into the claims registry. The predicate name and
return sort are checked against `rules/booklogic-schema.edn`.
Failures raise `LLMLiftRejected` which the ingest layer catches and
surfaces as a structured `:llm-lift-rejected` defect.
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class LLMLiftError(RuntimeError):
    """Raised when an LLM lift attempt fails for an infrastructural
    reason (missing SDK, unreachable endpoint, missing API key)."""


class LLMLiftRejected(ValueError):
    """REQ-LLMLIFT-043: raised when an LLM proposal fails schema
    validation. The ingest layer catches this and emits a structured
    `:llm-lift-rejected` defect rather than a silent OPAQUE atom."""


# ---------------------------------------------------------------------------
# Provider interface + 4 concrete backends (REQ-LLMLIFT-041)
# ---------------------------------------------------------------------------


class LLMLiftProvider(ABC):
    """Abstract LLM lift backend.

    Subclasses implement `extract(claim_id, canonical_text, emit_template)
    -> dict | None` and produce a candidate typed-atom proposal.
    """

    name: str = "abstract"

    @abstractmethod
    def extract(
        self,
        *,
        claim_id: str,
        canonical_text: str,
        emit_template: str,
    ) -> dict[str, Any] | None:
        ...


class StubLift(LLMLiftProvider):
    """REQ-LLMLIFT-048: offline stub provider for CI.

    Returns a canned JSON response without touching the network. Used
    by the test suite to exercise every code path without needing API
    keys or live endpoints.
    """

    name = "stub"

    def __init__(self, canned_response: str = "{}") -> None:
        self._response = canned_response

    def extract(self, *, claim_id, canonical_text, emit_template):
        if not self._response:
            return None
        return json.loads(self._response)


class OpenAILift(LLMLiftProvider):
    """REQ-LLMLIFT-041: OpenAI provider via the `openai` SDK.

    Requires OPENAI_API_KEY. The SDK is an optional extra; if the
    package is not installed, raises LLMLiftError with a clear
    install hint.
    """

    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model

    def extract(self, *, claim_id, canonical_text, emit_template):
        if not os.environ.get("OPENAI_API_KEY"):
            raise LLMLiftError(
                "OPENAI_API_KEY is not set; set OPENAI_API_KEY to use the "
                "openai provider (NEUROSYM_LLM_PROVIDER=openai)"
            )
        try:
            import openai
        except ImportError as e:
            raise LLMLiftError(
                "openai package not installed; pip install openai "
                "(declared as optional extra)"
            ) from e
        client = openai.OpenAI()
        prompt = _build_prompt(canonical_text, emit_template)
        timeout_ms = int(os.environ.get("VERIFIER_LLM_TIMEOUT_MS", "30000"))
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            timeout=timeout_ms / 1000.0,
        )
        return json.loads(response.choices[0].message.content)


class AnthropicLift(LLMLiftProvider):
    """REQ-LLMLIFT-041: Anthropic provider via the `anthropic` SDK.

    Requires ANTHROPIC_API_KEY. SDK is an optional extra.
    """

    name = "anthropic"

    def __init__(self, model: str = "claude-haiku-4-5") -> None:
        self.model = model

    def extract(self, *, claim_id, canonical_text, emit_template):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMLiftError(
                "ANTHROPIC_API_KEY is not set; set ANTHROPIC_API_KEY to "
                "use the anthropic provider (NEUROSYM_LLM_PROVIDER=anthropic)"
            )
        try:
            import anthropic
        except ImportError as e:
            raise LLMLiftError(
                "anthropic package not installed; pip install anthropic "
                "(declared as optional extra)"
            ) from e
        client = anthropic.Anthropic()
        timeout_ms = int(os.environ.get("VERIFIER_LLM_TIMEOUT_MS", "30000"))
        prompt = _build_prompt(canonical_text, emit_template)
        msg = client.messages.create(
            model=self.model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout_ms / 1000.0,
        )
        return json.loads(msg.content[0].text)


class LocalLift(LLMLiftProvider):
    """REQ-LLMLIFT-041: Local provider that POSTs to a local Ollama
    HTTP endpoint. No SDK dependency — uses urllib from the stdlib.
    """

    name = "local"

    def __init__(self, model: str = "llama3:8b") -> None:
        self.model = model
        self.base_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    def extract(self, *, claim_id, canonical_text, emit_template):
        import urllib.error
        import urllib.request

        prompt = _build_prompt(canonical_text, emit_template)
        body = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }).encode()
        timeout = int(os.environ.get("VERIFIER_LLM_TIMEOUT_MS", "30000")) / 1000.0
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read())
        except urllib.error.URLError as e:
            raise LLMLiftError(
                f"ollama unreachable at {self.base_url}: {e}"
            ) from e
        return json.loads(payload["response"])


def _build_prompt(canonical_text: str, emit_template: str) -> str:
    """Zero-shot prompt template. The emit_template carries the
    expected atom shape; the prompt asks the LLM to produce that
    shape from the claim text. JSON-only output."""
    return (
        "Extract a typed atom from this text matching the template.\n"
        f"Template: {emit_template}\n"
        f"Text: {canonical_text}\n"
        'Respond with JSON only: {"predicate": ":NAME", '
        '"subject": ":S", "value": <typed-value>}. '
        "Use only predicate names from the template. JSON only, no prose."
    )


def get_provider(name: str | None = None) -> LLMLiftProvider:
    """REQ-LLMLIFT-040: factory — read NEUROSYM_LLM_PROVIDER and
    return the right backend. Default is 'stub' (offline CI).
    """
    name = name or os.environ.get("NEUROSYM_LLM_PROVIDER", "stub").lower()
    if name == "stub":
        return StubLift()
    if name == "openai":
        return OpenAILift()
    if name == "anthropic":
        return AnthropicLift()
    if name == "local":
        return LocalLift()
    raise LLMLiftError(
        f"unknown NEUROSYM_LLM_PROVIDER {name!r}; "
        "valid: stub | openai | anthropic | local"
    )


# ---------------------------------------------------------------------------
# Schema validation (REQ-LLMLIFT-042, 043)
# ---------------------------------------------------------------------------


def _kw_name(v: Any) -> str | None:
    """Best-effort name-of-keyword: accepts Keyword, str ':foo', or str 'foo'."""
    if v is None:
        return None
    if hasattr(v, "name"):
        return v.name
    if isinstance(v, str):
        return v.lstrip(":")
    return str(v)


def validate_proposal(schema_path: Path | str, proposal: dict) -> dict:
    """REQ-LLMLIFT-042: validate an LLM proposal against
    `booklogic-schema.edn` (the standard Tier 1 REQ-EDN-052 shape).

    Checks:
      1. The `predicate` name exists in the schema's `:predicates` map.
      2. The `value` matches the predicate's declared `:return` sort
         (`:int`, `:real`, `:bool`, `:string`, `:keyword`).

    Raises `LLMLiftRejected` on failure (REQ-LLMLIFT-043). Returns the
    validated proposal dict unchanged on success.
    """
    schema_path = Path(schema_path)
    # Late import: keeps top-level imports light + matches existing pattern
    # in ingest_ledger.py which imports lazily through scripts._io.
    from scripts._edn_reader import Keyword
    from scripts._io import read_edn_file

    if not schema_path.exists():
        raise LLMLiftRejected(
            f"booklogic-schema.edn not found at {schema_path}; "
            "every :backend :llm lift requires a schema"
        )
    schema = read_edn_file(schema_path)
    predicates = schema.get(Keyword("predicates"), {}) or {}

    pred_raw = proposal.get("predicate")
    pred_name = _kw_name(pred_raw)
    if pred_name is None:
        raise LLMLiftRejected(
            f"proposal missing :predicate field; got {proposal!r}"
        )

    # Schema keys are Keyword objects — match by .name.
    matched_spec = None
    for key, spec in predicates.items():
        if _kw_name(key) == pred_name:
            matched_spec = spec
            break
    if matched_spec is None:
        known = sorted(_kw_name(k) or "" for k in predicates)
        raise LLMLiftRejected(
            f"unknown predicate {pred_name!r}; not in booklogic-schema.edn "
            f"(known: {known})"
        )

    expected_return = _kw_name(matched_spec.get(Keyword("return")))
    value = proposal.get("value")

    if expected_return == "int":
        # bool is a subclass of int — reject so :int doesn't accept True.
        if isinstance(value, bool) or not isinstance(value, int):
            raise LLMLiftRejected(
                f"predicate {pred_name!r} expects :int, "
                f"got {type(value).__name__} ({value!r})"
            )
    elif expected_return == "real":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise LLMLiftRejected(
                f"predicate {pred_name!r} expects :real, "
                f"got {type(value).__name__} ({value!r})"
            )
    elif expected_return == "bool":
        if not isinstance(value, bool):
            raise LLMLiftRejected(
                f"predicate {pred_name!r} expects :bool, "
                f"got {type(value).__name__} ({value!r})"
            )
    elif expected_return == "string":
        if not isinstance(value, str):
            raise LLMLiftRejected(
                f"predicate {pred_name!r} expects :string, "
                f"got {type(value).__name__} ({value!r})"
            )
    elif expected_return == "keyword":
        if not (isinstance(value, str) or hasattr(value, "name")):
            raise LLMLiftRejected(
                f"predicate {pred_name!r} expects :keyword, "
                f"got {type(value).__name__} ({value!r})"
            )
    # Unknown return sort: pass-through (schema may extend later).
    return proposal
