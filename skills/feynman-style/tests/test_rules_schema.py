import pytest
pytestmark = pytest.mark.windows_canary

import json
from pathlib import Path

RULES = Path("assets/feynman-rules.json")

def test_rules_load_and_have_partition():
    data = json.loads(RULES.read_text(encoding="utf-8"))
    assert "linter_class" in data
    cls = data["linter_class"]
    # Russell surface linters Feynman overrides -> "surface"
    assert cls["no-hedging"] == "surface"
    assert cls["signal-density"] == "surface"
    # Integrity always enforced
    assert cls["preserve-argument"] == "integrity"
    assert cls["footnote-orphan"] == "integrity"
    # every value is one of the two classes
    assert set(cls.values()) <= {"surface", "integrity"}

def test_rules_have_budgets_and_maps():
    data = json.loads(RULES.read_text(encoding="utf-8"))
    assert isinstance(data["budgets"]["reading-grade"], (int, float))
    assert data["latinate_substitutions"]["utilize"] == "use"
    assert "max_sentence_word_count" in data
