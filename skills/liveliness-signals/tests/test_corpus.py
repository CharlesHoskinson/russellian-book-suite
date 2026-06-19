"""Cites REQ-LIVE-001, REQ-LIVE-002 (register partition)."""
import json
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.corpus import register_for, load_corpus, REGISTERS


def test_register_for_majority_vote():
    assert register_for(["systems_tradeoff", "problem_framing"], "") == "technical-exposition"
    assert register_for(["concrete_analogy", "scale_setting"], "") == "narrative-editorial"
    assert register_for(["conviction", "momentum", "candor"], "") == "polemic"


def test_register_for_defaults_to_narrative_on_tie_or_unknown():
    assert register_for([], "") == "narrative-editorial"
    assert register_for(["totally_unknown_tag"], "") == "narrative-editorial"


def test_load_corpus_attaches_register(tmp_path):
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"paragraphs": [
        {"id": "p1", "text": "a b c.", "rhetorical_move": "", "tags": ["conviction", "momentum"]},
        {"id": "p2", "text": "d e f.", "rhetorical_move": "", "tags": ["concrete_analogy"]},
    ]}), encoding="utf-8")
    rows = load_corpus(idx)
    assert {r["id"]: r["register"] for r in rows} == {"p1": "polemic", "p2": "narrative-editorial"}
    assert all(set(r) == {"id", "text", "register"} for r in rows)
    assert REGISTERS == ("technical-exposition", "narrative-editorial", "polemic")
