"""REQ-LLMLIFT-040, 041, 048: LLM-backed lift extractors.

Tests the provider interface and offline-stub responder. The
openai/anthropic SDK tests are guarded by `pytest.importorskip` so CI
runs deterministically without the optional extras.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._llm_lift import (  # noqa: E402
    AnthropicLift,
    LLMLiftError,
    LLMLiftProvider,
    LocalLift,
    OpenAILift,
    StubLift,
    get_provider,
)


# ---------------------------------------------------------------------------
# REQ-LLMLIFT-041, 048: provider interface + offline stub
# ---------------------------------------------------------------------------


def test_stub_provider_returns_canned_atom():
    """REQ-LLMLIFT-048: StubLift returns the canned JSON without any
    network access — the workhorse for offline CI."""
    provider = StubLift(
        canned_response='{"predicate": ":trial-n", "subject": ":t1", "value": 42}'
    )
    atom = provider.extract(
        claim_id="c-001",
        canonical_text="trial enrolled 42 patients",
        emit_template="(fact ?claim-id :trial :trial-n (parse-int ?v))",
    )
    assert atom["predicate"] == ":trial-n"
    assert atom["value"] == 42
    assert atom["subject"] == ":t1"


def test_stub_provider_empty_response_returns_none():
    """Empty canned response — provider returned no atom."""
    provider = StubLift(canned_response="")
    atom = provider.extract(
        claim_id="c-001",
        canonical_text="no extractable atom here",
        emit_template="(fact ...)",
    )
    assert atom is None


def test_each_provider_class_is_an_llm_lift_provider():
    """REQ-LLMLIFT-041: every concrete provider inherits the abstract base."""
    assert issubclass(StubLift, LLMLiftProvider)
    assert issubclass(OpenAILift, LLMLiftProvider)
    assert issubclass(AnthropicLift, LLMLiftProvider)
    assert issubclass(LocalLift, LLMLiftProvider)


def test_get_provider_defaults_to_stub(monkeypatch):
    """Default provider when NEUROSYM_LLM_PROVIDER is unset is `stub`
    so CI runs offline."""
    monkeypatch.delenv("NEUROSYM_LLM_PROVIDER", raising=False)
    p = get_provider()
    assert isinstance(p, StubLift)


def test_get_provider_unknown_raises():
    with pytest.raises(LLMLiftError):
        get_provider("nonsense-backend")


# ---------------------------------------------------------------------------
# REQ-LLMLIFT-041: OpenAI / Anthropic SDK paths (skipped if SDK missing)
# ---------------------------------------------------------------------------


def test_openai_requires_api_key(monkeypatch):
    """REQ-LLMLIFT-048: if NEUROSYM_LLM_PROVIDER=openai and OPENAI_API_KEY
    is unset, the error message names the missing variable."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    p = OpenAILift()
    with pytest.raises(LLMLiftError, match="OPENAI_API_KEY"):
        p.extract(claim_id="c", canonical_text="x", emit_template="t")


def test_anthropic_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = AnthropicLift()
    with pytest.raises(LLMLiftError, match="ANTHROPIC_API_KEY"):
        p.extract(claim_id="c", canonical_text="x", emit_template="t")


def test_openai_provider_smoke(monkeypatch):
    """When the openai SDK is importable, OpenAILift constructs cleanly.
    Actual HTTP is not exercised — production-provider tests are
    opt-in via `make test-llm-online`.
    """
    pytest.importorskip("openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-only-for-construct-path")
    p = OpenAILift(model="gpt-4o-mini")
    assert p.name == "openai"
    assert p.model == "gpt-4o-mini"


def test_anthropic_provider_smoke(monkeypatch):
    pytest.importorskip("anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-only-for-construct-path")
    p = AnthropicLift(model="claude-haiku-4-5")
    assert p.name == "anthropic"
    assert p.model == "claude-haiku-4-5"


def test_local_provider_uses_ollama_url(monkeypatch):
    """LocalLift reads OLLAMA_URL from the environment."""
    monkeypatch.setenv("OLLAMA_URL", "http://example.invalid:11434")
    p = LocalLift()
    assert p.base_url == "http://example.invalid:11434"
