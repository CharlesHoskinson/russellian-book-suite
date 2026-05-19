"""REQ-CORPUS-046: scale-eval report contains six metrics + scaling profile."""
from __future__ import annotations

from pathlib import Path


def test_six_metrics_present_and_scaling_profile_named(repo_root: Path) -> None:
    report = repo_root / "docs" / "eval" / "2026-05-19-scale-eval-report.md"
    assert report.exists(), f"missing scale-eval report: {report}"
    text = report.read_text(encoding="utf-8").lower()

    required_metrics = [
        "claims ingested",
        "claims-per-minute",
        "peak rss",
        "defect detection rate",
        "false-positive rate",
        "phase with longest runtime",
    ]
    missing = [m for m in required_metrics if m not in text]
    assert not missing, f"scale-eval report missing metric labels: {missing}"

    assert "scaling profile" in text, "missing 'scaling profile' section"
