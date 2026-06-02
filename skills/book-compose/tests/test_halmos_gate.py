import pytest
pytestmark = pytest.mark.windows_canary
import json, time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.chapter_contract_check import _compute_metrics


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
