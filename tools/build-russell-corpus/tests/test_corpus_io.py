import json
from pathlib import Path

import pytest

from scripts.corpus_io import append_jsonl, read_jsonl
from scripts.corpus_io import read_index, append_index_entries


def test_append_then_read_jsonl_roundtrips(tmp_path: Path) -> None:
    target = tmp_path / "ledger.jsonl"
    append_jsonl(target, {"id": "a", "n": 1})
    append_jsonl(target, {"id": "b", "n": 2})
    rows = read_jsonl(target)
    assert rows == [{"id": "a", "n": 1}, {"id": "b", "n": 2}]


def test_read_jsonl_missing_file_returns_empty_list(tmp_path: Path) -> None:
    assert read_jsonl(tmp_path / "absent.jsonl") == []


def test_read_index_returns_paragraphs(tmp_path: Path) -> None:
    idx_path = tmp_path / "index.json"
    idx_path.write_text(json.dumps({
        "version": "0.1.0",
        "paragraph_count": 1,
        "sources": {"problems": {"title": "x", "url": "u", "copyright_status": "public_domain_us", "mode": ["m"]}},
        "paragraphs": [
            {"id": "problems-001", "source": "problems", "line_hint": 433,
             "rhetorical_move": "rm", "tags": ["t1"]},
        ],
    }))
    idx = read_index(idx_path)
    assert idx["paragraph_count"] == 1
    assert idx["paragraphs"][0]["id"] == "problems-001"


def test_append_index_entries_updates_count_and_preserves_existing(tmp_path: Path) -> None:
    idx_path = tmp_path / "index.json"
    idx_path.write_text(json.dumps({
        "version": "0.1.0",
        "paragraph_count": 1,
        "sources": {"problems": {"title": "x", "url": "u", "copyright_status": "public_domain_us", "mode": ["m"]}},
        "paragraphs": [
            {"id": "problems-001", "source": "problems", "line_hint": 433,
             "rhetorical_move": "rm", "tags": ["t1"]},
        ],
    }))
    new_entries = [
        {"id": "problems-051", "source": "problems", "line_hint": 812,
         "rhetorical_move": "rm2", "tags": ["t2"],
         "content_locator": "Philosophy, throughout"},
    ]
    append_index_entries(idx_path, new_entries)
    idx = json.loads(idx_path.read_text())
    assert idx["paragraph_count"] == 2
    assert len(idx["paragraphs"]) == 2
    assert idx["paragraphs"][1]["id"] == "problems-051"
    assert idx["paragraphs"][1]["content_locator"] == "Philosophy, throughout"
    # original entry preserved verbatim
    assert idx["paragraphs"][0]["id"] == "problems-001"


def test_append_index_entries_rejects_intra_batch_duplicate_ids(tmp_path: Path) -> None:
    idx_path = tmp_path / "index.json"
    idx_path.write_text(json.dumps({
        "version": "0.1.0",
        "paragraph_count": 1,
        "sources": {"problems": {"title": "x", "url": "u", "copyright_status": "public_domain_us", "mode": ["m"]}},
        "paragraphs": [
            {"id": "problems-001", "source": "problems", "line_hint": 433,
             "rhetorical_move": "rm", "tags": ["t1"]},
        ],
    }))
    duplicates = [
        {"id": "problems-051", "source": "problems", "line_hint": 812,
         "rhetorical_move": "rm-a", "tags": ["t2"]},
        {"id": "problems-051", "source": "problems", "line_hint": 813,
         "rhetorical_move": "rm-b", "tags": ["t3"]},
    ]
    with pytest.raises(ValueError, match="problems-051"):
        append_index_entries(idx_path, duplicates)
    # The original index must be unchanged.
    idx = json.loads(idx_path.read_text())
    assert idx["paragraph_count"] == 1
    assert len(idx["paragraphs"]) == 1
