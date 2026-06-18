import pytest
pytestmark = [pytest.mark.windows_canary, pytest.mark.needs_spacy_model]
import json
import os
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.chapter_contract_check import _compute_metrics, check_draft


def _draft(tmp_path, verdict: dict | None):
    d = tmp_path / "chapters" / "drafts" / "ch-09"
    d.mkdir(parents=True)
    dp = d / "draft.md"; dp.write_text("# C9\nbody\n", encoding="utf-8")
    if verdict is not None:
        time.sleep(0.01)
        (d / "halmos-verdict.json").write_text(json.dumps(verdict), encoding="utf-8")
    return dp


def test_halmos_metric_reads_verdict(tmp_path):
    dp = _draft(tmp_path, {"halmos_critical_count": 0, "reviews_complete": True})
    m = _compute_metrics(dp)
    assert m["halmos_critical_count"] == 0


def test_halmos_metric_absent_is_failing_sentinel(tmp_path):
    dp = _draft(tmp_path, None)
    m = _compute_metrics(dp)
    assert m["halmos_critical_count"] == 999


def test_halmos_metric_stale_verdict_is_failing_sentinel(tmp_path):
    # A valid passing verdict that predates the current draft revision must not
    # satisfy the `== 0` gate: a stale verdict left over from a prior draft is
    # backdated below, so the mtime check must coerce it to the 999 sentinel.
    dp = _draft(tmp_path, {"halmos_critical_count": 0, "reviews_complete": True})
    verdict = dp.parent / "halmos-verdict.json"
    stale = dp.stat().st_mtime - 5
    os.utime(verdict, (stale, stale))
    m = _compute_metrics(dp)
    assert m["halmos_critical_count"] == 999


def test_halmos_malformed_verdict_is_failing_sentinel(tmp_path):
    # Invalid JSON newer than the draft must still coerce to the 999 sentinel:
    # a corrupt verdict cannot be allowed to satisfy `== 0`.
    dp = _draft(tmp_path, None)
    time.sleep(0.01)
    (dp.parent / "halmos-verdict.json").write_text("not json", encoding="utf-8")
    m = _compute_metrics(dp)
    assert m["halmos_critical_count"] == 999


def test_halmos_reviews_complete_present_fresh(tmp_path):
    dp = _draft(tmp_path, {"halmos_critical_count": 0, "reviews_complete": True})
    m = _compute_metrics(dp)
    assert m["halmos_reviews_complete"] is True


def test_halmos_reviews_complete_absent(tmp_path):
    dp = _draft(tmp_path, None)
    m = _compute_metrics(dp)
    assert m["halmos_reviews_complete"] is False


def test_gate_blocks_on_nonzero_count(tmp_path):
    dp = _draft(tmp_path, {"halmos_critical_count": 3, "reviews_complete": True})
    result = check_draft(dp, {"acceptance_tests": ["halmos_critical_count == 0"]})
    assert result.passes is False
    assert "halmos_critical_count == 0" in result.failed_tests


def test_gate_passes_on_zero_count(tmp_path):
    dp = _draft(tmp_path, {"halmos_critical_count": 0, "reviews_complete": True})
    result = check_draft(dp, {"acceptance_tests": ["halmos_critical_count == 0"]})
    assert result.passes is True
    assert result.failed_tests == []
