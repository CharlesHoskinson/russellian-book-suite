import json
from pathlib import Path
from scripts.sentinel import aggregate


def test_critical_d9_d13_are_hard_fail(tmp_path: Path):
    qa = tmp_path / "qa"; qa.mkdir()
    (qa / "defects.json").write_text(json.dumps({"defects": [
        {"class": "D9",  "severity": "critical", "where": "ch01", "detail": "orphan"},
        {"class": "D11", "severity": "critical", "where": "ch02", "detail": "failed entailment"},
        {"class": "D13", "severity": "critical", "where": "doc",  "detail": "verification unsat"},
        {"class": "D12", "severity": "important", "where": "ch03", "detail": "unadvanced"},
    ]}), encoding="utf-8")
    report = aggregate(tmp_path)
    hard = {t["class"] for t in report.hard_fail_tickets}
    assert {"D9", "D11", "D13"} <= hard, hard
    assert "D12" not in hard  # important stays soft
    assert report.hard_fail_count >= 3
