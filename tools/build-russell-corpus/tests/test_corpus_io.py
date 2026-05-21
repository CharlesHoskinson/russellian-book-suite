from pathlib import Path
from scripts.corpus_io import append_jsonl, read_jsonl


def test_append_then_read_jsonl_roundtrips(tmp_path: Path) -> None:
    target = tmp_path / "ledger.jsonl"
    append_jsonl(target, {"id": "a", "n": 1})
    append_jsonl(target, {"id": "b", "n": 2})
    rows = read_jsonl(target)
    assert rows == [{"id": "a", "n": 1}, {"id": "b", "n": 2}]


def test_read_jsonl_missing_file_returns_empty_list(tmp_path: Path) -> None:
    assert read_jsonl(tmp_path / "absent.jsonl") == []
