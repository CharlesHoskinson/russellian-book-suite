import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_ai_vocabulary import lint_ai_vocabulary
from scripts.lint_sentence_rhythm import lint_sentence_rhythm


def test_ai_vocabulary_runs(tmp_path):
    md = tmp_path / "v.md"
    md.write_text("Clearly this approach works seamlessly.\n", encoding="utf-8")
    out = lint_ai_vocabulary(md)
    assert isinstance(out, list)
    assert out
    assert all("rule" in f and "line" in f for f in out)

def test_sentence_rhythm_runs(tmp_path):
    md = tmp_path / "r.md"
    md.write_text("It runs. It stops. It runs. It stops. It runs again now.\n", encoding="utf-8")
    out = lint_sentence_rhythm(md)
    assert isinstance(out, list)
    assert out
    assert all("rule" in f and "line" in f for f in out)
