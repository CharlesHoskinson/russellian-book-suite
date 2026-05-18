from scripts.workspace import init_workspace
from scripts.counter_claims import append_counter_claim, read_counter_claims
from scripts.promote_addressed import promote_addressed


def _seed_cc(tmp_path):
    init_workspace(tmp_path)
    append_counter_claim(tmp_path, {
        "id": "cc-2026-abcdef", "target_claim_id": "clm-2026-000001",
        "text": "Ferry network has consolidated.", "disagreement_vector": "scope",
        "status": "open",
        "provenance": {"generator": "abduction-v1", "prompt_sha256": "0"*64},
        "created_at": "2026-05-11T00:00:00Z", "addressed_in_chapter": None,
    })


def test_promotes_open_to_addressed(tmp_path):
    _seed_cc(tmp_path)
    n = promote_addressed(tmp_path, chapter_id="ch07", addressed_ids=["cc-2026-abcdef"])
    assert n == 1
    items = read_counter_claims(tmp_path)
    latest = [r for r in items if r["id"] == "cc-2026-abcdef"][-1]
    assert latest["status"] == "addressed"
    assert latest["addressed_in_chapter"] == "ch07"


def test_promote_idempotent_skips_already_addressed(tmp_path):
    _seed_cc(tmp_path)
    promote_addressed(tmp_path, chapter_id="ch07", addressed_ids=["cc-2026-abcdef"])
    n = promote_addressed(tmp_path, chapter_id="ch07", addressed_ids=["cc-2026-abcdef"])
    assert n == 0  # already addressed; no new record appended


def test_promote_skips_unknown_id(tmp_path):
    _seed_cc(tmp_path)
    n = promote_addressed(tmp_path, chapter_id="ch07", addressed_ids=["cc-9999-zzzzzz"])
    assert n == 0
