import json
from pathlib import Path

from scripts.chapter_slice import slice_for_chapter


def _seed_ledger(tmp_path: Path, records: list[dict]) -> None:
    (tmp_path / "claims").mkdir(parents=True, exist_ok=True)
    with (tmp_path / "claims" / "ledger.jsonl").open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _claim(cid: str, status: str, chapters: tuple = ("ch07",)) -> dict:
    return {
        "claim_id": cid,
        "canonical_text": "Test.",
        "status": status,
        "claim_type": "fact",
        "confidence": 0.7,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "supports_chapters": list(chapters),
        "created_at": "2026-05-11T00:00:00Z",
    }


def test_slice_excludes_refuted(tmp_path):
    _seed_ledger(tmp_path, [
        _claim("clm-2026-000001", "verified"),
        _claim("clm-2026-000002", "refuted"),
    ])
    contract = {"chapter_id": "ch07"}
    out = slice_for_chapter(tmp_path, "ch07", contract)
    ids = {r["claim_id"] for r in out}
    assert "clm-2026-000001" in ids
    assert "clm-2026-000002" not in ids


def test_slice_includes_refuted_when_pinned(tmp_path):
    _seed_ledger(tmp_path, [
        _claim("clm-2026-000001", "verified"),
        _claim("clm-2026-000002", "refuted"),
    ])
    contract = {"chapter_id": "ch07", "force_include_refuted": ["clm-2026-000002"]}
    out = slice_for_chapter(tmp_path, "ch07", contract)
    ids = {r["claim_id"] for r in out}
    assert "clm-2026-000002" in ids


def test_slice_excludes_disputed_by_default(tmp_path):
    _seed_ledger(tmp_path, [_claim("clm-2026-000001", "disputed")])
    contract = {"chapter_id": "ch07"}
    out = slice_for_chapter(tmp_path, "ch07", contract)
    assert out == []


def test_slice_includes_disputed_when_contract_accepts(tmp_path):
    _seed_ledger(tmp_path, [_claim("clm-2026-000001", "disputed")])
    contract = {"chapter_id": "ch07", "accept_disputed": True}
    out = slice_for_chapter(tmp_path, "ch07", contract)
    assert len(out) == 1


def test_slice_excludes_superseded(tmp_path):
    _seed_ledger(tmp_path, [_claim("clm-2026-000001", "superseded")])
    contract = {"chapter_id": "ch07"}
    out = slice_for_chapter(tmp_path, "ch07", contract)
    assert out == []


def test_slice_excludes_wrong_chapter(tmp_path):
    _seed_ledger(tmp_path, [
        _claim("clm-2026-000001", "verified", chapters=("ch08",)),
    ])
    contract = {"chapter_id": "ch07"}
    out = slice_for_chapter(tmp_path, "ch07", contract)
    assert out == []


def test_slice_latest_record_wins(tmp_path):
    """When a claim appears twice in the ledger (e.g. status transition),
    the last record's status governs."""
    first = _claim("clm-2026-000001", "verified")
    second = dict(first)
    second["status"] = "refuted"
    _seed_ledger(tmp_path, [first, second])
    contract = {"chapter_id": "ch07"}
    out = slice_for_chapter(tmp_path, "ch07", contract)
    assert out == []


def test_slice_empty_ledger(tmp_path):
    _seed_ledger(tmp_path, [])
    out = slice_for_chapter(tmp_path, "ch07", {"chapter_id": "ch07"})
    assert out == []


def test_slice_force_include_refuted_only_when_in_chapter(tmp_path):
    """force_include_refuted only rescues claims already supporting the chapter."""
    _seed_ledger(tmp_path, [
        _claim("clm-2026-000001", "refuted", chapters=("ch08",)),
    ])
    contract = {"chapter_id": "ch07", "force_include_refuted": ["clm-2026-000001"]}
    out = slice_for_chapter(tmp_path, "ch07", contract)
    assert out == []
