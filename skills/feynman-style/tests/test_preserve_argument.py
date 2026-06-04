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


def test_sentence_split_and_synonym_warming_passes():
    # A Russell sentence split into Feynman fragments, plus a synonym swap, must
    # not read as a dropped claim (regression: README Feynman pass false positives).
    before = ("These clusters are treated as provisional hypotheses, never as an alphabet. "
              "A claim of decipherment is permitted only when stable glyphs and stable tokenization hold.")
    after = ("Treat these as guesses, never as an alphabet. "
             "You may claim a decipherment only when two things hold. Stable glyphs. Stable tokenization.")
    report = preserve_argument(before, after)
    assert report.ok, report.violations


def test_local_flow_reorder_does_not_trip():
    # Swapping one adjacent pair in a longer passage is a legitimate flow move.
    before = "A is one. B is two. C is three. D is four. E is five."
    after = "A is one. C is three. B is two. D is four. E is five."
    report = preserve_argument(before, after)
    assert not any(v["kind"] == "reordered-claim" for v in report.violations), report.violations
