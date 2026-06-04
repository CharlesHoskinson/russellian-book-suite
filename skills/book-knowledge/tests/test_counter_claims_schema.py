import pytest
from scripts.counter_claims import (
    validate_counter_claim, append_counter_claim, read_counter_claims,
    next_counter_claim_id, CounterClaimError,
)
from scripts.workspace import init_workspace

BASE = {
    "id": "cc-0001-abcdef",
    "target_claim_id": "clm-2026-000001",
    "text": "Some rival hypothesis stated as one sentence.",
    "disagreement_vector": "scope",
    "status": "open",
    "provenance": {"generator": "abduction-v1", "prompt_sha256": "0"*64},
    "created_at": "2026-05-11T00:00:00Z",
    "addressed_in_chapter": None,
}

def test_valid_record_accepts():
    validate_counter_claim(BASE)

def test_invalid_status_rejected():
    with pytest.raises(CounterClaimError):
        validate_counter_claim({**BASE, "status": "approved"})

def test_invalid_disagreement_vector_rejected():
    with pytest.raises(CounterClaimError):
        validate_counter_claim({**BASE, "disagreement_vector": "vibes"})

def test_id_pattern_enforced():
    with pytest.raises(CounterClaimError):
        validate_counter_claim({**BASE, "id": "cc-0001-XYZ"})

def test_append_and_read(tmp_path):
    init_workspace(tmp_path)
    append_counter_claim(tmp_path, BASE)
    items = read_counter_claims(tmp_path)
    assert len(items) == 1
    assert items[0]["id"] == "cc-0001-abcdef"


def test_next_id_avoids_ledger_collision(tmp_path, monkeypatch):
    """next_counter_claim_id must not return an id already in the ledger."""
    import scripts.counter_claims as cc
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    init_workspace(tmp_path)
    existing = f"cc-{year}-aaaaaa"
    append_counter_claim(tmp_path, {**BASE, "id": existing})
    # token_hex first yields the colliding suffix, then a fresh one.
    suffixes = iter(["aaaaaa", "bbbbbb"])
    monkeypatch.setattr(cc.secrets, "token_hex", lambda n: next(suffixes))
    got = next_counter_claim_id(tmp_path)
    assert got == f"cc-{year}-bbbbbb"
    assert got != existing


def test_next_id_avoids_in_batch_collision(tmp_path, monkeypatch):
    """Ids minted earlier in the same batch (reserved) are not reused."""
    import scripts.counter_claims as cc
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    init_workspace(tmp_path)
    suffixes = iter(["cccccc", "dddddd"])
    monkeypatch.setattr(cc.secrets, "token_hex", lambda n: next(suffixes))
    got = next_counter_claim_id(tmp_path, reserved={f"cc-{year}-cccccc"})
    assert got == f"cc-{year}-dddddd"
