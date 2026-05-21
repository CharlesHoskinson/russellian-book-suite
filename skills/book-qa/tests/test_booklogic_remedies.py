# skills/book-qa/tests/test_booklogic_remedies.py
"""REQ-DSL-040 + REQ-QA-PIPE-010 + REQ-QA-PIPE-012: booklogic_remedies adapter."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

import pytest

from scripts.booklogic_remedies import (
    load_remedies,
    match_remedies_against_verdict,
    RemedyError,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_load_remedies_reads_two_entries() -> None:
    remedies = load_remedies(FIXTURES / "remedies_sample.edn")
    assert len(remedies) == 2
    names = {r["id"] for r in remedies}
    assert "W001-unsat-core-to-refutation" in names
    assert "W002-low-conf-disputed"         in names


def test_match_unsat_core_pattern_against_verdict() -> None:
    remedies = load_remedies(FIXTURES / "remedies_sample.edn")
    verdict  = {"verdict": "unsat",
                "core":    ["clm-2026-000008", "prose-ch-02-001"]}
    proposals = match_remedies_against_verdict(remedies, verdict)
    # The unsat-core pattern should match each core entry.
    assert len(proposals) == 2
    for p in proposals:
        assert p["remedy_id"] == "W001-unsat-core-to-refutation"
        assert p["requires"]  == "human-review"
        assert p["transition"]["to"] == "refuted"


def test_human_review_blocks_auto_apply_field() -> None:
    """REQ-QA-PIPE-012: :requires :human-review sets auto_apply=False."""
    remedies = load_remedies(FIXTURES / "remedies_sample.edn")
    verdict  = {"verdict": "unsat", "core": ["clm-2026-000008"]}
    proposals = match_remedies_against_verdict(remedies, verdict)
    assert all(p["auto_apply"] is False for p in proposals)


def test_auto_apply_remedy_passes_through() -> None:
    remedies = load_remedies(FIXTURES / "remedies_sample.edn")
    verdict  = {"verdict": "sat",
                "low_confidence": ["clm-2026-000009"]}
    proposals = match_remedies_against_verdict(remedies, verdict)
    assert any(p["remedy_id"] == "W002-low-conf-disputed" for p in proposals)
    w002 = next(p for p in proposals if p["remedy_id"] == "W002-low-conf-disputed")
    assert w002["auto_apply"] is True
    assert w002["transition"]["to"] == "disputed"


def test_no_match_returns_empty() -> None:
    remedies = load_remedies(FIXTURES / "remedies_sample.edn")
    verdict  = {"verdict": "sat", "core": []}
    proposals = match_remedies_against_verdict(remedies, verdict)
    assert proposals == []


def test_load_remedies_missing_file_returns_empty() -> None:
    assert load_remedies(Path("/nonexistent/path/remedies.edn")) == []


def test_malformed_remedy_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.edn"
    p.write_text("{:version 1 :remedies [{:id \"X\"}]}", encoding="utf-8")
    with pytest.raises(RemedyError, match="missing"):
        load_remedies(p)


def test_match_against_minimal_verdict_shape() -> None:
    remedies = load_remedies(FIXTURES / "remedies_sample.edn")
    # Verdict carries only the verdict status — nothing to match against.
    proposals = match_remedies_against_verdict(remedies, {"verdict": "unknown"})
    assert proposals == []
