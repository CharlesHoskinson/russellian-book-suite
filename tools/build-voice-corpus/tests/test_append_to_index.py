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


def test_reindex_does_not_collide(tmp_path: Path):
    """4.3: appending the same video again seeds the counter from existing
    entries, continuing the ids instead of colliding on hoskinson-<vid>-000."""
    p = tmp_path / "index.json"
    init_index(p, version="0.1.0", copyright_policy="own-content",
               sources={"channel": "@charleshoskinsoncrypto"})
    batch = [{"video_id": "abc123", "t_start": "00:00:01", "text": "one",
              "rhetorical_move": "m1", "tags": ["a"]}]
    append_passages(p, batch)
    append_passages(p, batch)  # second run must not raise on id collision
    idx = read_index(p)
    ids = [e["id"] for e in idx["paragraphs"]]
    assert ids == ["hoskinson-abc123-000", "hoskinson-abc123-001"]
    assert idx["paragraph_count"] == 2
