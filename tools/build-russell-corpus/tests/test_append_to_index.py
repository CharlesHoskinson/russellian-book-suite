import json
from pathlib import Path

from scripts.append_to_index import append_verified_to_index, regenerate_corpus_map


def _seed_index(tmp_path: Path) -> Path:
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({
        "version": "0.1.0",
        "paragraph_count": 1,
        "sources": {"problems": {"title": "x", "url": "u", "copyright_status": "public_domain_us", "mode": ["m"]}},
        "paragraphs": [
            {"id": "problems-001", "source": "problems", "line_hint": 433,
             "rhetorical_move": "rm", "tags": ["t1"]},
        ],
    }, indent=2), encoding="utf-8")
    return idx


def _seed_verified(tmp_path: Path) -> Path:
    verified = tmp_path / "verified.jsonl"
    rows = [
        {"candidate_id": "problems-051",
         "source_id": "problems",
         "source_url": "u",
         "line_hint": 812,
         "content_locator": "Philosophy, throughout its history,",
         "paragraph_text": "Philosophy, throughout its history, has consisted of two parts inharmoniously blended.",
         "rhetorical_move_tag": "domain_contrast",
         "calibration_lesson": "Russell splits philosophy into two domains."}
    ]
    verified.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return verified


def test_append_verified_to_index_projects_to_existing_schema(tmp_path: Path) -> None:
    idx_path = _seed_index(tmp_path)
    verified_path = _seed_verified(tmp_path)
    append_verified_to_index(verified_path=verified_path, index_path=idx_path)
    idx = json.loads(idx_path.read_text())
    assert idx["paragraph_count"] == 2
    new_entry = idx["paragraphs"][1]
    assert new_entry["id"] == "problems-051"
    assert new_entry["source"] == "problems"
    assert new_entry["line_hint"] == 812
    assert new_entry["rhetorical_move"] == "Russell splits philosophy into two domains."
    assert new_entry["tags"] == ["domain_contrast"]
    assert new_entry["content_locator"] == "Philosophy, throughout its history,"


def test_regenerate_corpus_map_emits_table_row_for_new_entry(tmp_path: Path) -> None:
    idx_path = _seed_index(tmp_path)
    verified_path = _seed_verified(tmp_path)
    append_verified_to_index(verified_path=verified_path, index_path=idx_path)
    map_path = tmp_path / "russell-corpus-map.md"
    regenerate_corpus_map(index_path=idx_path, out_path=map_path)
    text = map_path.read_text(encoding="utf-8")
    assert "problems-001" in text
    assert "problems-051" in text
    assert "Russell splits philosophy into two domains." in text
