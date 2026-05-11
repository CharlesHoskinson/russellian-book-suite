from pathlib import Path
from scripts.lint_passive_voice import lint_passive_voice


def test_detects_passive_constructions():
    findings = lint_passive_voice(Path("tests/fixtures/passive_sample.md"))
    sentences = [f["sentence"] for f in findings]
    assert any("provisioned" in s for s in sentences)
    assert any("loaded" in s for s in sentences)
    assert any("handled" in s for s in sentences)
    assert any("written" in s for s in sentences)


def test_skips_active_voice_sentences():
    findings = lint_passive_voice(Path("tests/fixtures/passive_sample.md"))
    actives = [s for s in (f["sentence"] for f in findings)
               if "script provisions" in s or "daemon loads" in s]
    assert actives == []


def test_returns_empty_for_compliant():
    findings = lint_passive_voice(Path("tests/fixtures/compliant_sample.md"))
    assert findings == []


def test_records_position_and_rule():
    findings = lint_passive_voice(Path("tests/fixtures/passive_sample.md"))
    for f in findings:
        assert f["rule"] == "active-voice"
        assert f["line"] >= 1
        assert "sentence" in f
