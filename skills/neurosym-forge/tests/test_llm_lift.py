"""REQ-LLMLIFT-040..045, 048: LLM-backed lift extractors.

Tests the provider interface, schema validation, SQLite cache, and
offline-stub responder. The openai/anthropic SDK tests are guarded by
`pytest.importorskip` so CI runs deterministically without the optional
extras.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._llm_lift import (  # noqa: E402
    AnthropicLift,
    LLMLiftError,
    LLMLiftProvider,
    LLMLiftRejected,
    LocalLift,
    OpenAILift,
    StubLift,
    cached_extract,
    get_provider,
    validate_proposal,
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


# ---------------------------------------------------------------------------
# REQ-LLMLIFT-042, 043: schema validation
# ---------------------------------------------------------------------------


def _write_schema(tmp_path: Path) -> Path:
    schema = tmp_path / "booklogic-schema.edn"
    schema.write_text(
        '{:version 1 :sorts [:trial] '
        ':predicates {:trial-n {:arg-sorts [:trial] :return :int}'
        '             :trial-p {:arg-sorts [:trial] :return :real}'
        '             :trial-name {:arg-sorts [:trial] :return :string}'
        '             :trial-pass {:arg-sorts [:trial] :return :bool}}}',
        encoding="utf-8",
    )
    return schema


def test_validate_proposal_accepts_valid_int(tmp_path):
    schema = _write_schema(tmp_path)
    atom = validate_proposal(
        schema, {"predicate": ":trial-n", "subject": ":t1", "value": 42}
    )
    assert atom["predicate"] == ":trial-n"
    assert atom["value"] == 42


def test_validate_proposal_accepts_valid_real(tmp_path):
    schema = _write_schema(tmp_path)
    atom = validate_proposal(
        schema, {"predicate": ":trial-p", "subject": ":t1", "value": 0.04}
    )
    assert atom["value"] == 0.04


def test_validate_proposal_rejects_unknown_predicate(tmp_path):
    schema = _write_schema(tmp_path)
    with pytest.raises(LLMLiftRejected, match="unknown predicate"):
        validate_proposal(
            schema, {"predicate": ":bogus", "subject": ":t1", "value": 42}
        )


def test_validate_proposal_rejects_wrong_int_sort(tmp_path):
    """An :int predicate that receives a float must reject — the
    framework refuses to corrupt the downstream constraint surface
    with mis-typed atoms (REQ-LLMLIFT-042)."""
    schema = _write_schema(tmp_path)
    with pytest.raises(LLMLiftRejected, match="expects :int"):
        validate_proposal(
            schema, {"predicate": ":trial-n", "subject": ":t1", "value": 42.5}
        )


def test_validate_proposal_rejects_wrong_real_sort(tmp_path):
    schema = _write_schema(tmp_path)
    with pytest.raises(LLMLiftRejected, match="expects :real"):
        validate_proposal(
            schema, {"predicate": ":trial-p", "subject": ":t1", "value": "0.04"}
        )


def test_validate_proposal_rejects_wrong_bool_sort(tmp_path):
    schema = _write_schema(tmp_path)
    with pytest.raises(LLMLiftRejected, match="expects :bool"):
        validate_proposal(
            schema, {"predicate": ":trial-pass", "subject": ":t1", "value": 1}
        )


def test_validate_proposal_rejects_missing_predicate(tmp_path):
    schema = _write_schema(tmp_path)
    with pytest.raises(LLMLiftRejected, match="missing :predicate"):
        validate_proposal(schema, {"subject": ":t1", "value": 42})


def test_validate_proposal_missing_schema_file_raises(tmp_path):
    missing = tmp_path / "no-such-schema.edn"
    with pytest.raises(LLMLiftRejected, match="booklogic-schema.edn not found"):
        validate_proposal(missing, {"predicate": ":x", "value": 1})


# ---------------------------------------------------------------------------
# REQ-LLMLIFT-045: SQLite cache + hit-count stats
# ---------------------------------------------------------------------------


def test_cache_disabled_falls_through_to_provider(monkeypatch, tmp_path):
    """When NEUROSYM_LLM_CACHE != 1, cached_extract calls the provider
    every time (no DB writes)."""
    monkeypatch.delenv("NEUROSYM_LLM_CACHE", raising=False)
    monkeypatch.setenv("NEUROSYM_LLM_CACHE_PATH", str(tmp_path / "cache.db"))
    provider = StubLift(
        canned_response='{"predicate": ":foo", "subject": ":s", "value": 1}'
    )
    a = cached_extract(
        provider, claim_id="c", canonical_text="x", emit_template="t"
    )
    assert a["predicate"] == ":foo"
    # Cache DB was never created since caching was off.
    assert not (tmp_path / "cache.db").exists()


def test_cache_hit_returns_same_atom_and_bumps_stats(monkeypatch, tmp_path):
    """REQ-LLMLIFT-045: identical (canonical_text_sha256, lift_id) hits
    the SQLite cache; the cache_stats table records the hit count."""
    monkeypatch.setenv("NEUROSYM_LLM_CACHE", "1")
    cache_db = tmp_path / "cache.db"
    monkeypatch.setenv("NEUROSYM_LLM_CACHE_PATH", str(cache_db))
    provider = StubLift(
        canned_response='{"predicate": ":foo", "subject": ":s", "value": 1}'
    )
    a1 = cached_extract(
        provider,
        claim_id="c1",
        canonical_text="x",
        emit_template="t",
        lift_id="L001",
    )
    a2 = cached_extract(
        provider,
        claim_id="c1",
        canonical_text="x",
        emit_template="t",
        lift_id="L001",
    )
    assert a1 == a2
    assert cache_db.exists()
    db = sqlite3.connect(str(cache_db))
    rows = list(
        db.execute(
            "SELECT hit_count FROM cache_stats "
            "WHERE claim_id = 'c1' AND lift_id = 'L001'"
        )
    )
    db.close()
    assert rows and rows[0][0] >= 2, (
        f"expected hit_count >= 2 after 2 cached_extract calls, got {rows!r}"
    )


def test_cache_distinct_lift_ids_are_separate(monkeypatch, tmp_path):
    """Same canonical_text, different lift_id — must not collide."""
    monkeypatch.setenv("NEUROSYM_LLM_CACHE", "1")
    monkeypatch.setenv("NEUROSYM_LLM_CACHE_PATH", str(tmp_path / "cache.db"))
    p1 = StubLift(canned_response='{"predicate": ":a", "value": 1}')
    p2 = StubLift(canned_response='{"predicate": ":b", "value": 2}')
    a = cached_extract(
        p1, claim_id="c", canonical_text="x", emit_template="t", lift_id="L1"
    )
    b = cached_extract(
        p2, claim_id="c", canonical_text="x", emit_template="t", lift_id="L2"
    )
    assert a["predicate"] == ":a"
    assert b["predicate"] == ":b"


def test_cache_none_proposal_is_not_stored(monkeypatch, tmp_path):
    """When the provider returns None, do not store anything in cache."""
    monkeypatch.setenv("NEUROSYM_LLM_CACHE", "1")
    cache_db = tmp_path / "cache.db"
    monkeypatch.setenv("NEUROSYM_LLM_CACHE_PATH", str(cache_db))
    provider = StubLift(canned_response="")
    a = cached_extract(
        provider, claim_id="c", canonical_text="x", emit_template="t"
    )
    assert a is None
    # The DB exists (we touched it) but llm_lift_cache has no entries.
    db = sqlite3.connect(str(cache_db))
    rows = list(db.execute("SELECT COUNT(*) FROM llm_lift_cache"))
    db.close()
    assert rows[0][0] == 0
