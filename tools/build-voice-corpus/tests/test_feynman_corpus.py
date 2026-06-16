import json
from pathlib import Path

import yaml

CORPUS = Path(__file__).resolve().parents[3] / "skills" / "russellian-style" / "assets" / "feynman-corpus" / "index.json"
ALLOW = Path(__file__).parents[1] / "assets" / "feynman-sources.yaml"


def test_feynman_corpus_has_envelope():
    idx = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert idx["paragraph_count"] == len(idx["paragraphs"])
    assert "pointer" in idx["copyright_policy"].lower() or "no verbatim" in idx["copyright_policy"].lower()


def test_feynman_entries_are_pointers_only():
    idx = json.loads(CORPUS.read_text(encoding="utf-8"))
    allowed = set(yaml.safe_load(ALLOW.read_text(encoding="utf-8"))["sources"].keys())
    for e in idx["paragraphs"]:
        assert "text" not in e, f"verbatim text leaked into {e['id']}"
        assert e["source"] in allowed
        assert e["rhetorical_move"]
        assert isinstance(e["tags"], list)
