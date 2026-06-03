import pytest
pytestmark = pytest.mark.windows_canary

from scripts.preserve_argument import preserve_argument, PreservationReport


def test_clean_warming_passes():
    before = "The cache stores results. A second request reads from disk. This avoids a network call."
    after = ("Here's the trick: the cache just keeps your results around. "
             "So the second time you ask, it grabs them off the disk — "
             "and you skip the network call entirely.")
    report = preserve_argument(before, after)
    assert isinstance(report, PreservationReport)
    assert report.ok, report.violations

def test_dropped_claim_fails():
    before = "The cache stores results. A second request reads from disk. This avoids a network call."
    after = "Here's the trick: the cache keeps your results around."
    report = preserve_argument(before, after)
    assert not report.ok
    assert any(v["kind"] == "dropped-claim" for v in report.violations)

def test_introduced_number_fails():
    before = "The cache stores results to avoid a network call."
    after = "The cache stores results, cutting latency by 80 percent and avoiding the network call."
    report = preserve_argument(before, after)
    assert not report.ok
    assert any(v["kind"] == "introduced-fact" for v in report.violations)

def test_reordered_claim_fails():
    before = "Alpha covers ignition systems. Beta covers cooling pumps."
    after = "Beta covers the cooling pumps. Alpha covers the ignition systems."
    report = preserve_argument(before, after)
    assert not report.ok
    assert any(v["kind"] == "reordered-claim" for v in report.violations)
