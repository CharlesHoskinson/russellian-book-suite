"""lint_ai_vocabulary: humanizer-delegated catalog + Russell-specific overlay."""
from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_false_certainty_flagged(tmp_path):
    from scripts.lint_ai_vocabulary import lint_ai_vocabulary
    text = "The system clearly succeeds. Obviously, the user benefits."
    findings = lint_ai_vocabulary(_write(tmp_path, text))
    ids = {f["pattern_id"] for f in findings}
    assert "false_certainty" in ids


def test_magic_adverb_flagged(tmp_path):
    from scripts.lint_ai_vocabulary import lint_ai_vocabulary
    text = "The platform quietly orchestrates workflows and seamlessly bridges teams."
    findings = lint_ai_vocabulary(_write(tmp_path, text))
    ids = {f["pattern_id"] for f in findings}
    assert "magic_adverb" in ids


def test_transition_adverb_starter_flagged(tmp_path):
    from scripts.lint_ai_vocabulary import lint_ai_vocabulary
    text = (
        "The team shipped the feature. Moreover, the team measured adoption. "
        "Furthermore, the dashboards updated nightly."
    )
    findings = lint_ai_vocabulary(_write(tmp_path, text))
    ids = {f["pattern_id"] for f in findings}
    assert "transition_adverb_starter" in ids


def test_no_violations_in_clean_text(tmp_path):
    from scripts.lint_ai_vocabulary import lint_ai_vocabulary
    text = (
        "The committee voted seven to two. The minority filed a brief dissent. "
        "Bermuda's parliament adjourned at six in the evening."
    )
    findings = lint_ai_vocabulary(_write(tmp_path, text))
    russell_specific = [
        f for f in findings
        if not f["pattern_id"].startswith("humanizer:")
    ]
    assert russell_specific == []


def test_supplement_loads():
    from scripts.lint_ai_vocabulary import load_supplement
    supp = load_supplement()
    ids = {p["id"] for p in supp["patterns"]}
    assert {"false_certainty", "magic_adverb", "transition_adverb_starter"} <= ids
