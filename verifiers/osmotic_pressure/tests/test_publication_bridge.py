"""Phase T tests for the osmotic_pressure verifier's
manuscript-annotations.json emission (REQ-PUB-040, REQ-PUB-046).
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.verdict_to_qa import emit_manuscript_annotations


def test_manuscript_annotations_schema(tmp_path: Path) -> None:
    """REQ-PUB-040: emit_manuscript_annotations produces v1 schema."""
    verdict = {
        "status": "unsat",
        "defects": [
            {
                "claim_id": "c-001",
                "source_span": [120, 145],
                "severity": "critical",
                "message": "low n",
                "defect_confidence": 0.92,
            },
        ],
    }
    out = tmp_path / "manuscript-annotations.json"
    emit_manuscript_annotations(verdict, source_path="report.md", out_path=out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["source_path"] == "report.md"
    assert len(data["annotations"]) == 1
    ann = data["annotations"][0]
    assert ann["claim_id"] == "c-001"
    assert ann["source_span"] == [120, 145]
    assert ann["severity"] == "critical"
    assert ann["message"] == "low n"
    assert ann["defect_confidence"] == 0.92


def test_manuscript_annotations_passes_optional_fields(tmp_path: Path) -> None:
    """REQ-PUB-045: declared_severity / defect_id / constraint_id /
    see_also are passed through when present."""
    verdict = {
        "defects": [
            {
                "claim_id": "C042",
                "source_span": [10, 20],
                "severity": "soft",
                "declared_severity": "hard",
                "message": "downgraded",
                "defect_confidence": 0.4,
                "defect_id": "D042",
                "constraint_id": "X042",
                "see_also": ["C051", "C052", "C053"],
            },
        ],
    }
    out = tmp_path / "manuscript-annotations.json"
    emit_manuscript_annotations(verdict, source_path="m.md", out_path=out)
    data = json.loads(out.read_text(encoding="utf-8"))
    ann = data["annotations"][0]
    assert ann["declared_severity"] == "hard"
    assert ann["defect_id"] == "D042"
    assert ann["constraint_id"] == "X042"
    assert ann["see_also"] == ["C051", "C052", "C053"]


def test_manuscript_annotations_records_source_sha256(tmp_path: Path) -> None:
    """REQ-PUB-040: source_sha256 captured at verify time when bytes
    are supplied — enables stale-span detection downstream."""
    verdict = {"defects": []}
    out = tmp_path / "manuscript-annotations.json"
    emit_manuscript_annotations(
        verdict, source_path="m.md", out_path=out,
        source_bytes=b"hello world",
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    # sha256("hello world") = b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    assert data["source_sha256"] == (
        "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    )


def test_manuscript_annotations_empty_when_no_defects(tmp_path: Path) -> None:
    """REQ-PUB-040: sat verdicts produce an annotations: [] file."""
    verdict = {"status": "sat", "defects": []}
    out = tmp_path / "manuscript-annotations.json"
    emit_manuscript_annotations(verdict, source_path="m.md", out_path=out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["annotations"] == []


def test_manuscript_annotations_skips_malformed_defects(tmp_path: Path) -> None:
    """REQ-PUB-040: defects without a valid source_span are skipped
    (rather than crashing) so partial verdicts still produce output."""
    verdict = {
        "defects": [
            {"claim_id": "c-good", "source_span": [0, 5], "message": "ok",
             "severity": "hard", "defect_confidence": 0.5},
            {"claim_id": "c-bad-no-span", "message": "missing span"},
            {"claim_id": "c-bad-malformed", "source_span": "not a list"},
            "not even a dict",
        ],
    }
    out = tmp_path / "manuscript-annotations.json"
    emit_manuscript_annotations(verdict, source_path="m.md", out_path=out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["annotations"]) == 1
    assert data["annotations"][0]["claim_id"] == "c-good"
