import pytest
pytestmark = pytest.mark.windows_canary

import json
from pathlib import Path

IDX = Path("assets/feynman-corpus/index.json")

def test_index_well_formed():
    data = json.loads(IDX.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) >= 8
    moves = {e["rhetorical_move"] for e in data}
    assert {"analogy", "direct-address", "honest-doubt"} <= moves
    for e in data:
        assert {"source_id", "rhetorical_move", "text"} <= set(e)

def test_excerpts_are_short():
    data = json.loads(IDX.read_text(encoding="utf-8"))
    for e in data:
        if e["source_id"].startswith("synthetic"):
            continue
        assert len(e["text"].split()) <= 60  # quotation-length only
