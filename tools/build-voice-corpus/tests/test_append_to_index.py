from pathlib import Path

from scripts.corpus_io import init_index, read_index
from scripts.append_to_index import build_entry, append_passages


def test_build_entry_shape():
    e = build_entry(video_id="abc123", index=7, t_start="00:14:22",
                    text="Look, the thing people miss...",
                    rhetorical_move="reframes critique", tags=["candor"])
    assert e["id"] == "hoskinson-abc123-007"
    assert e["video_id"] == "abc123"
    assert e["t_start"] == "00:14:22"
    assert e["text"].startswith("Look")
    assert e["tags"] == ["candor"]


def test_append_passages_writes_entries(tmp_path: Path):
    p = tmp_path / "index.json"
    init_index(p, version="0.1.0", copyright_policy="own-content", sources={"channel": "@charleshoskinsoncrypto"})
    passages = [
        {"video_id": "abc123", "t_start": "00:00:01", "text": "one", "rhetorical_move": "m1", "tags": ["a"]},
        {"video_id": "abc123", "t_start": "00:00:05", "text": "two", "rhetorical_move": "m2", "tags": ["b"]},
    ]
    append_passages(p, passages)
    idx = read_index(p)
    assert idx["paragraph_count"] == 2
    assert idx["paragraphs"][0]["id"] == "hoskinson-abc123-000"
    assert idx["paragraphs"][1]["id"] == "hoskinson-abc123-001"
