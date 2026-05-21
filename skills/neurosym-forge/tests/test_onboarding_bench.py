"""REQ-EVAL-050..055: onboarding-bench harness sanity tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import csv
import subprocess
import sys
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"
BENCH = EVAL_DIR / "onboarding-bench.py"
AGGREGATE = EVAL_DIR / "aggregate_runs.py"
PROMPTS = EVAL_DIR / "prompts"


def test_three_prompts_exist():
    assert PROMPTS.exists(), f"missing prompts dir at {PROMPTS}"
    prompts = list(PROMPTS.glob("*.md"))
    assert len(prompts) >= 3, f"expected >=3 prompts, got {[p.name for p in prompts]}"


def test_stub_run_succeeds(tmp_path):
    result = subprocess.run(
        [sys.executable, str(BENCH), "--backend", "stub", "--out", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    csvs = list(tmp_path.glob("*.csv"))
    assert csvs, f"no CSV produced under {tmp_path}; stderr: {result.stderr}"
    # Every row must report SUCCESS for the stub backend.
    with csvs[0].open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "CSV had no rows"
    for row in rows:
        assert row["outcome"] == "SUCCESS", row
        assert row["backend"] == "stub"


def test_aggregator_produces_report(tmp_path):
    # First run the harness to populate a runs dir.
    runs_dir = tmp_path / "runs"
    subprocess.run(
        [sys.executable, str(BENCH), "--backend", "stub", "--out", str(runs_dir)],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    out_path = tmp_path / "report.md"
    subprocess.run(
        [
            sys.executable,
            str(AGGREGATE),
            "--runs-dir",
            str(runs_dir),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    assert out_path.exists(), "aggregator did not write the report"
    body = out_path.read_text(encoding="utf-8")
    assert "Onboarding-bench report" in body
    assert "Reach-ci" in body
    assert "Top 5 doc gaps" in body
