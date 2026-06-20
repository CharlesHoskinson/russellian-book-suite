from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "russellian-style" / "SKILL.md"
GUIDE = ROOT / "skills" / "russellian-style" / "references" / "triadic-voice-guide.md"


def test_guide_exists():
    assert GUIDE.exists()


def test_skill_references_triadic_voice_and_corpora():
    text = SKILL.read_text(encoding="utf-8")
    assert "triadic-voice-guide.md" in text
    assert "feynman-corpus" in text
    assert "hoskinson-corpus" in text
