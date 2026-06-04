import json
from pathlib import Path

from scripts.derive_vocabulary import derive_controlled_vocabulary


FIXTURE = Path(__file__).parent / "fixtures" / "existing_index_sample.json"


def test_derive_vocabulary_returns_one_entry_per_unique_tag(tmp_path: Path) -> None:
    out = tmp_path / "vocabulary.json"
    derive_controlled_vocabulary(index_path=FIXTURE, out_path=out)
    vocab = json.loads(out.read_text())
    assert "tags" in vocab
    expected_slugs = {
        "concrete_example", "abstraction_grounding",
        "counterexample", "argument_turn",
        "human_figure", "antithesis",
        "concession", "domain_contrast",
        "reversal", "paragraph_turn",
    }
    actual_slugs = {t["slug"] for t in vocab["tags"]}
    assert actual_slugs == expected_slugs


def test_derive_vocabulary_each_tag_carries_anchors(tmp_path: Path) -> None:
    out = tmp_path / "vocabulary.json"
    derive_controlled_vocabulary(index_path=FIXTURE, out_path=out)
    vocab = json.loads(out.read_text())
    tag_by_slug = {t["slug"]: t for t in vocab["tags"]}
    assert "concrete_example" in tag_by_slug
    anchor_ids = tag_by_slug["concrete_example"]["anchor_ids"]
    assert "problems-001" in anchor_ids


def test_derive_vocabulary_emits_version_and_count(tmp_path: Path) -> None:
    out = tmp_path / "vocabulary.json"
    derive_controlled_vocabulary(index_path=FIXTURE, out_path=out)
    vocab = json.loads(out.read_text())
    assert vocab["version"] == "0.1.0"
    assert vocab["tag_count"] == len(vocab["tags"])
