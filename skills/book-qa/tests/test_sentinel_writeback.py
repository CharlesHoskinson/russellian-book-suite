"""Test that Sentinel calls propose_writeback after aggregation.

Wiring added in Task 3.7: aggregate() accepts an optional ``version``
kwarg; when supplied it calls propose_writeback so writeback artifacts
land alongside QA outputs.
"""
import pytest

pytestmark = pytest.mark.windows_canary

import json
from pathlib import Path

from scripts.sentinel import aggregate


def _seed_findings(ws: Path) -> None:
    (ws / "qa").mkdir(parents=True)
    (ws / "claims").mkdir(parents=True)
    (ws / "qa" / "lint-findings.json").write_text(
        json.dumps({"tickets": [
            {
                "id": "ch07-D11-04",
                "class": "unsupported_claim",
                "claim_id": "clm-2026-000001",
                "claim_current_status": "verified",
                "severity": "critical",
            }
        ]}),
        encoding="utf-8",
    )
    (ws / "qa" / "swarm-findings.json").write_text(
        json.dumps({"tickets": []}),
        encoding="utf-8",
    )


def test_sentinel_runs_propose_writeback(tmp_path: Path) -> None:
    _seed_findings(tmp_path)
    aggregate(tmp_path, version="v6-test")
    assert (tmp_path / "qa" / "proposed-transitions.jsonl").exists()
    assert (tmp_path / "qa" / "ledger-writeback-v6-test.md").exists()


def test_sentinel_writeback_skipped_without_version(tmp_path: Path) -> None:
    """When version is omitted Sentinel still aggregates without error."""
    _seed_findings(tmp_path)
    report = aggregate(tmp_path)  # no version arg
    assert report.total == 0     # no stage-1 defects.json, no chapter tickets
    assert not (tmp_path / "qa" / "proposed-transitions.jsonl").exists()
