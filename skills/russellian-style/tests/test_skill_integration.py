import re
from pathlib import Path

import yaml

from scripts.style_pass_report import build_report
from scripts.lint_hedges import lint_hedges
from scripts.lint_passive_voice import lint_passive_voice
from scripts.lint_signal_density import lint_signal_density


def _split_before_after(path: Path) -> tuple[Path, Path, dict]:
    text = path.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    metadata = yaml.safe_load(fm_match.group(1))
    body = text[fm_match.end():]
    before = body.split("## BEFORE", 1)[1].split("## AFTER", 1)[0].strip()
    after = body.split("## AFTER", 1)[1].strip()
    before_path = path.with_suffix(".before.md")
    after_path = path.with_suffix(".after.md")
    before_path.write_text(before, encoding="utf-8")
    after_path.write_text(after, encoding="utf-8")
    return before_path, after_path, metadata


def test_before_passage_triggers_expected_findings(tmp_path):
    fixture = Path("tests/fixtures/before_after/01_bloat_to_axiom.md")
    before, after, meta = _split_before_after(fixture)
    try:
        hedges = lint_hedges(before)
        passives = lint_passive_voice(before)
        signal = lint_signal_density(before)
        assert len(hedges) >= meta["expected_findings"]["no-hedging"]
        assert len(passives) >= meta["expected_findings"]["active-voice"]
        assert len(signal) >= meta["expected_findings"]["signal-density"]
    finally:
        before.unlink(missing_ok=True)
        after.unlink(missing_ok=True)


def test_after_passage_passes_all_linters():
    fixture = Path("tests/fixtures/before_after/01_bloat_to_axiom.md")
    before, after, _ = _split_before_after(fixture)
    try:
        report = build_report(after)
        assert "hedge_count: 0" in report
        assert "modifier_budget_violations: 0" in report
    finally:
        before.unlink(missing_ok=True)
        after.unlink(missing_ok=True)


def test_full_run_emits_report_with_all_acceptance_metrics(tmp_path):
    fixture = Path("tests/fixtures/before_after/01_bloat_to_axiom.md")
    before, _, _ = _split_before_after(fixture)
    try:
        report = build_report(before)
        for metric in ("hedge_count:", "passive_voice_ratio:",
                       "modifier_budget_violations:", "parallel_structure_violations:"):
            assert metric in report
    finally:
        before.unlink(missing_ok=True)
        Path("tests/fixtures/before_after/01_bloat_to_axiom.after.md").unlink(missing_ok=True)
