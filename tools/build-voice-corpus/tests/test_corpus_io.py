import json
from pathlib import Path

import pytest

from scripts.corpus_io import read_index, append_index_entries, init_index


def test_init_index_creates_envelope(tmp_path: Path):
    p = tmp_path / "index.json"
    init_index(p, version="0.1.0", copyright_policy="own-content", sources={"yt": {"channel": "x"}})
    idx = read_index(p)
    assert idx["paragraph_count"] == 0
    assert idx["paragraphs"] == []
    assert idx["sources"] == {"yt": {"channel": "x"}}


def test_append_entries_updates_count(tmp_path: Path):
    p = tmp_path / "index.json"
    init_index(p, version="0.1.0", copyright_policy="own-content", sources={})
    append_index_entries(p, [{"id": "hoskinson-001", "text": "a"}])
    idx = read_index(p)
    assert idx["paragraph_count"] == 1
    assert idx["paragraphs"][0]["id"] == "hoskinson-001"


def test_append_rejects_duplicate_id(tmp_path: Path):
    p = tmp_path / "index.json"
    init_index(p, version="0.1.0", copyright_policy="own-content", sources={})
    append_index_entries(p, [{"id": "hoskinson-001", "text": "a"}])
    with pytest.raises(ValueError):
        append_index_entries(p, [{"id": "hoskinson-001", "text": "b"}])
