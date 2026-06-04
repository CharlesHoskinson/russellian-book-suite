import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.pdf_extract import normalize_text
from scripts.build_delta_profile import build_profile_from_texts, build_profile


def test_normalize_fixes_mojibake():
    raw = "She�s got a birthday—not today—but soon."
    out = normalize_text(raw)
    assert "�" not in out
    assert "—" not in out  # em-dash normalized to hyphen

def test_build_profile_from_texts_returns_relative_freqs():
    texts = ["atoms jiggle and jiggle", "the atoms move and jiggle around"]
    prof = build_profile_from_texts(texts, top_n=5)
    assert abs(sum(prof.values()) - 1.0) < 1e-6
    assert "jiggle" in prof

def test_build_profile_empty_drop_falls_back(tmp_path):
    # empty drop dir -> returns None, signals fallback (does not raise)
    result = build_profile(corpus_dir=tmp_path, out_path=tmp_path / "p.json")
    assert result is None
