import pytest

pytestmark = pytest.mark.windows_canary

import json
from pathlib import Path

from scripts.lint_signal_density import lint_signal_density


def test_flags_modifier_heavy_sentences():
    findings = lint_signal_density(Path("tests/fixtures/modifier_heavy_sample.md"))
    flagged = [f["sentence"] for f in findings]
    assert any("extraordinarily robust" in s for s in flagged)


def test_does_not_flag_clean_sentences():
    findings = lint_signal_density(Path("tests/fixtures/modifier_heavy_sample.md"))
    flagged = [f["sentence"] for f in findings]
    assert not any("script provisions the server in 12 seconds" in s for s in flagged)


def test_returns_modifier_ratio():
    findings = lint_signal_density(Path("tests/fixtures/modifier_heavy_sample.md"))
    assert all("modifier_ratio" in f for f in findings)
    assert all(f["modifier_ratio"] > 0.20 for f in findings)


def test_compliant_sample_has_no_findings():
    findings = lint_signal_density(Path("tests/fixtures/compliant_sample.md"))
    assert findings == []


def test_short_sentences_exempt_from_modifier_check(tmp_path):
    # Even a heavy modifier ratio in a 5-token sentence should pass
    text = "# Sample\n\nA tall, dark, mysterious stranger arrived."
    f = tmp_path / "short.md"
    f.write_text(text, encoding="utf-8")
    findings = lint_signal_density(f)
    assert findings == []


def test_modifier_budget_default_is_025():
    from scripts.lint_common import load_rules
    rules = load_rules()
    assert rules["modifier_budget_ratio"] == 0.25


def test_overrides_exclude_words_from_modifier_count(tmp_path, monkeypatch):
    # Build a sentence with several modifiers; without override it should flag,
    # with override applied to those modifier words it should not.
    text = (
        "# Sample\n\n"
        "The bermudian rental outer non-status committee surprisingly delivered "
        "the bermudian rental outer report.\n"
    )
    md = tmp_path / "domain.md"
    md.write_text(text, encoding="utf-8")

    # Ensure no override leaks in -> baseline finds at least one issue.
    monkeypatch.delenv("RUSSELLIAN_OVERRIDES", raising=False)
    # Clear cached overrides if any (function reads env on every call).
    baseline = lint_signal_density(md)

    # Now write an override file that suppresses the domain modifier words.
    override = tmp_path / "overrides.json"
    override.write_text(
        json.dumps({"skip_modifier_words": ["bermudian", "rental", "outer", "non-status"]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("RUSSELLIAN_OVERRIDES", str(override))
    after = lint_signal_density(md)

    # Expect override to reduce or eliminate findings vs baseline.
    assert len(after) <= len(baseline)
    assert len(baseline) >= 1
    assert len(after) < len(baseline) or len(after) == 0
