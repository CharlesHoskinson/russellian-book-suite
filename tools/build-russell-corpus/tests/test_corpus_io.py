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


from scripts.corpus_io import content_locator, paragraph_in_source, find_paragraph_line


FIXTURE_SOURCE = Path(__file__).parent / "fixtures" / "source_cache" / "problems_subset.html"


def test_content_locator_returns_first_120_chars_stripped() -> None:
    text = "  Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine.  "
    assert content_locator(text) == "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to th"
    assert len(content_locator(text)) == 120


def test_paragraph_in_source_matches_verbatim() -> None:
    para = "The failure to separate these two with sufficient clarity has been a source of much confused thinking."
    assert paragraph_in_source(para, FIXTURE_SOURCE) is True


def test_paragraph_in_source_rejects_hallucinated() -> None:
    para = "Philosophy proves that all dogs are mortal and that Socrates is a dog."
    assert paragraph_in_source(para, FIXTURE_SOURCE) is False


def test_find_paragraph_line_returns_locator_line_number() -> None:
    locator = "The failure to separate"
    line = find_paragraph_line(locator, FIXTURE_SOURCE)
    assert isinstance(line, int)
    assert line >= 1


def test_paragraph_in_source_matches_line_wrapped_html(tmp_path: Path) -> None:
    """Paragraph present in source but wrapped across multiple lines must still match."""
    wrapped = tmp_path / "wrapped.html"
    wrapped.write_text(
        "<html><body>\n"
        "<p>The failure to separate these two\n"
        "with sufficient clarity has been a source\n"
        "of much confused thinking.</p>\n"
        "</body></html>\n",
        encoding="utf-8",
    )
    paragraph = "The failure to separate these two with sufficient clarity has been a source of much confused thinking."
    assert paragraph_in_source(paragraph, wrapped) is True
