import json
from scripts.io_utils import read_jsonl, latest_per


def test_read_jsonl_skips_blank_lines(tmp_path):
    p = tmp_path / "f.jsonl"
    p.write_text(json.dumps({"a": 1}) + "\n\n" + json.dumps({"a": 2}) + "\n",
                 encoding="utf-8")
    assert read_jsonl(p) == [{"a": 1}, {"a": 2}]


def test_read_jsonl_returns_empty_for_missing_file(tmp_path):
    assert read_jsonl(tmp_path / "nope.jsonl") == []


def test_read_jsonl_skips_corrupt_lines_with_warning(tmp_path, caplog):
    import logging
    p = tmp_path / "f.jsonl"
    p.write_text(
        json.dumps({"a": 1}) + "\n" +
        "this is not json\n" +
        json.dumps({"a": 3}) + "\n",
        encoding="utf-8",
    )
    with caplog.at_level(logging.WARNING):
        out = read_jsonl(p)
    assert out == [{"a": 1}, {"a": 3}]
    assert any("malformed JSONL line 2" in rec.message for rec in caplog.records)


def test_read_jsonl_resilient_to_truncated_final_line(tmp_path):
    p = tmp_path / "f.jsonl"
    p.write_text(
        json.dumps({"a": 1}) + "\n" +
        '{"a": 2, "b": ',  # truncated mid-line
        encoding="utf-8",
    )
    out = read_jsonl(p)
    assert out == [{"a": 1}]


def test_latest_per_last_write_wins():
    records = [{"id": "a", "v": 1}, {"id": "b", "v": 1}, {"id": "a", "v": 2}]
    latest = latest_per(records, "id")
    assert latest == {"a": {"id": "a", "v": 2}, "b": {"id": "b", "v": 1}}


def test_latest_per_skips_records_missing_key():
    records = [{"id": "a"}, {"name": "no-id"}, {"id": "b"}]
    latest = latest_per(records, "id")
    assert set(latest) == {"a", "b"}
