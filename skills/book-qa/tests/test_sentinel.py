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


def test_d12_stays_soft_even_if_critical(tmp_path: Path):
    qa = tmp_path / "qa"; qa.mkdir()
    (qa / "defects.json").write_text(json.dumps({"defects": [
        {"class": "D12", "severity": "critical", "where": "ch01", "detail": "unadvanced"},
    ]}), encoding="utf-8")
    report = aggregate(tmp_path)
    assert [t for t in report.hard_fail_tickets if t["class"] == "D12"] == []
    assert any(t["class"] == "D12" for t in report.soft_gate_tickets)


def test_corrupt_defects_json_is_hard_fail(tmp_path: Path):
    """4.2: a malformed Stage-1 defects.json surfaces as a synthetic hard-fail
    ticket, blocking the gate rather than crashing or passing silently."""
    qa = tmp_path / "qa"; qa.mkdir()
    (qa / "defects.json").write_text("{ not valid json", encoding="utf-8")
    report = aggregate(tmp_path)
    assert any(t["class"] == "C-CORRUPT" for t in report.hard_fail_tickets)
    assert report.hard_fail_count >= 1


def test_corrupt_chapter_ticket_is_hard_fail(tmp_path: Path):
    """4.2: a malformed Stage-2 chapter-ticket file is a synthetic hard-fail."""
    qa = tmp_path / "qa"; qa.mkdir()
    tix = qa / "chapter-tickets"; tix.mkdir()
    (tix / "ch-01.json").write_text("{ broken json", encoding="utf-8")
    report = aggregate(tmp_path)
    assert any(t["class"] == "C-CORRUPT" for t in report.hard_fail_tickets)
