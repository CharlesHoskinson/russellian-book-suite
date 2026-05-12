import json
from pathlib import Path

from tools.tag_load_bearing import tag_load_bearing


def _seed(ws: Path, records):
    (ws / "claims").mkdir(parents=True, exist_ok=True)
    with (ws / "claims" / "ledger.jsonl").open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _claim(cid, chapters, load_bearing=False):
    return {"claim_id": cid, "canonical_text": "Test.",
            "status": "verified", "claim_type": "fact", "confidence": 0.7,
            "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
            "supports_chapters": list(chapters),
            "load_bearing": load_bearing,
            "created_at": "2026-05-11T00:00:00Z"}


def test_tags_multi_chapter_claim(tmp_path):
    _seed(tmp_path, [
        _claim("clm-2026-000001", ["ch01", "ch02"]),
        _claim("clm-2026-000002", ["ch01"]),
    ])
    n = tag_load_bearing(tmp_path)
    assert n == 1
    records = [json.loads(l) for l in (tmp_path / "claims" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    latest = {r["claim_id"]: r for r in records}
    assert latest["clm-2026-000001"]["load_bearing"] is True
    assert latest["clm-2026-000002"].get("load_bearing", False) is False


def test_idempotent(tmp_path):
    _seed(tmp_path, [_claim("clm-2026-000001", ["ch01", "ch02"], load_bearing=True)])
    n = tag_load_bearing(tmp_path)
    assert n == 0


def test_no_ledger_is_noop(tmp_path):
    n = tag_load_bearing(tmp_path)
    assert n == 0
