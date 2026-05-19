"""REQ-CONFIDENCE-040..045 unit tests — confidence propagation.

Exercises the four pieces of Phase S:

- `compute_defect_confidence`  (min-of-chain rule, REQ-CONFIDENCE-040)
- `apply_confidence_downgrade` (advisory downgrade,  REQ-CONFIDENCE-041)
- `compute_verdict_confidence` (geometric mean,      REQ-CONFIDENCE-042)
- ingest-time `:confidence` validation              (REQ-CONFIDENCE-043)
- `:critical-defects` vs `:advisory-defects` split  (REQ-CONFIDENCE-044)
- three-chain regression case                       (REQ-CONFIDENCE-045)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verdict_to_qa import (  # noqa: E402
    apply_confidence_downgrade,
    compute_defect_confidence,
    compute_verdict_confidence,
    translate,
)


# ---------------------------------------------------------------------------
# REQ-CONFIDENCE-040: defect-confidence is min of unsat-core atom confidences
# ---------------------------------------------------------------------------


def test_defect_confidence_is_min_of_chain():
    chain = [
        {"id": "c-1", "confidence": 0.85},
        {"id": "c-2", "confidence": 0.62},
        {"id": "c-3", "confidence": 0.92},
    ]
    assert compute_defect_confidence(chain) == pytest.approx(0.62)


def test_defect_confidence_empty_chain_returns_one():
    """No atoms in the core => no evidence against => full confidence."""
    assert compute_defect_confidence([]) == pytest.approx(1.0)


def test_defect_confidence_dedups_repeated_claim_ids():
    """REQ-CONFIDENCE-040: min is over the *set* of distinct claim ids."""
    chain = [
        {"id": "c-1", "confidence": 0.4},
        {"id": "c-1", "confidence": 0.4},
        {"id": "c-2", "confidence": 0.9},
    ]
    assert compute_defect_confidence(chain) == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# REQ-CONFIDENCE-041: low-confidence chain downgrades to :advisory
# ---------------------------------------------------------------------------


def test_low_confidence_downgrades_to_advisory(monkeypatch):
    monkeypatch.setenv("VERIFIER_CONFIDENCE_THRESHOLD", "0.5")
    defect = {"severity": "critical", "defect_confidence": 0.3}
    apply_confidence_downgrade(defect)
    assert defect["severity"] == "advisory"
    assert defect["declared_severity"] == "critical"


def test_high_confidence_preserves_severity(monkeypatch):
    monkeypatch.setenv("VERIFIER_CONFIDENCE_THRESHOLD", "0.5")
    defect = {"severity": "critical", "defect_confidence": 0.85}
    apply_confidence_downgrade(defect)
    assert defect["severity"] == "critical"
    assert defect["declared_severity"] == "critical"


def test_explicit_threshold_overrides_env(monkeypatch):
    monkeypatch.setenv("VERIFIER_CONFIDENCE_THRESHOLD", "0.5")
    defect = {"severity": "critical", "defect_confidence": 0.45}
    apply_confidence_downgrade(defect, threshold=0.4)
    assert defect["severity"] == "critical"


def test_default_threshold_is_half():
    """No env override => default threshold = 0.5."""
    defect = {"severity": "critical", "defect_confidence": 0.49}
    apply_confidence_downgrade(defect)
    assert defect["severity"] == "advisory"


# ---------------------------------------------------------------------------
# REQ-CONFIDENCE-042: verdict-confidence is geometric mean across defects
# ---------------------------------------------------------------------------


def test_verdict_confidence_is_geometric_mean():
    defects = [
        {"defect_confidence": 0.8},
        {"defect_confidence": 0.5},
        {"defect_confidence": 0.9},
    ]
    expected = (0.8 * 0.5 * 0.9) ** (1.0 / 3)
    assert compute_verdict_confidence(defects) == pytest.approx(expected, rel=1e-6)


def test_verdict_confidence_zero_defects_is_one():
    assert compute_verdict_confidence([]) == pytest.approx(1.0)


def test_verdict_confidence_single_defect_equals_its_confidence():
    defects = [{"defect_confidence": 0.42}]
    assert compute_verdict_confidence(defects) == pytest.approx(0.42)


# ---------------------------------------------------------------------------
# REQ-CONFIDENCE-043: out-of-range / non-numeric confidence raises at ingest
# ---------------------------------------------------------------------------


def test_out_of_range_confidence_raises(tmp_path: Path) -> None:
    from scripts.ingest_ledger import IngestConfidenceError, ingest

    repo_root = PROJECT_ROOT.parent.parent
    predicates_path = (
        repo_root / "verifiers" / "bermuda" / "rules" / "predicates.edn"
    )
    if not predicates_path.exists():
        predicates_path = PROJECT_ROOT / "rules" / "predicates.edn"

    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        json.dumps(
            {
                "claim_id": "clm-2026-000999",
                "claim_type": "fact",
                "canonical_text": "Bermuda has nine parishes.",
                "status": "verified",
                "confidence": 1.4,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "claims.edn"
    with pytest.raises(IngestConfidenceError) as exc:
        ingest(bad, predicates_path, out)
    assert "clm-2026-000999" in str(exc.value)


def test_negative_confidence_raises(tmp_path: Path) -> None:
    from scripts.ingest_ledger import IngestConfidenceError, ingest

    repo_root = PROJECT_ROOT.parent.parent
    predicates_path = (
        repo_root / "verifiers" / "bermuda" / "rules" / "predicates.edn"
    )
    if not predicates_path.exists():
        predicates_path = PROJECT_ROOT / "rules" / "predicates.edn"

    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        json.dumps(
            {
                "claim_id": "clm-2026-000998",
                "claim_type": "fact",
                "canonical_text": "Bermuda has nine parishes.",
                "status": "verified",
                "confidence": -0.1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "claims.edn"
    with pytest.raises(IngestConfidenceError) as exc:
        ingest(bad, predicates_path, out)
    assert "clm-2026-000998" in str(exc.value)


def test_non_numeric_confidence_raises(tmp_path: Path) -> None:
    from scripts.ingest_ledger import IngestConfidenceError, ingest

    repo_root = PROJECT_ROOT.parent.parent
    predicates_path = (
        repo_root / "verifiers" / "bermuda" / "rules" / "predicates.edn"
    )
    if not predicates_path.exists():
        predicates_path = PROJECT_ROOT / "rules" / "predicates.edn"

    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        json.dumps(
            {
                "claim_id": "clm-2026-000997",
                "claim_type": "fact",
                "canonical_text": "Bermuda has nine parishes.",
                "status": "verified",
                "confidence": "high",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "claims.edn"
    with pytest.raises(IngestConfidenceError) as exc:
        ingest(bad, predicates_path, out)
    assert "clm-2026-000997" in str(exc.value)


def test_missing_confidence_defaults_to_one(tmp_path: Path) -> None:
    """Backwards-compat: pre-Tier-5 fixtures without :confidence keep working."""
    from scripts._edn_reader import Keyword
    from scripts._io import read_edn_file
    from scripts.ingest_ledger import ingest

    repo_root = PROJECT_ROOT.parent.parent
    predicates_path = (
        repo_root / "verifiers" / "bermuda" / "rules" / "predicates.edn"
    )
    if not predicates_path.exists():
        predicates_path = PROJECT_ROOT / "rules" / "predicates.edn"

    plain = tmp_path / "no_confidence.jsonl"
    plain.write_text(
        json.dumps(
            {
                "claim_id": "clm-2026-000900",
                "claim_type": "fact",
                "canonical_text": "Bermuda has nine parishes.",
                "status": "verified",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "claims.edn"
    ingest(plain, predicates_path, out)
    payload = read_edn_file(out)
    atoms = payload[Keyword("atoms")]
    assert len(atoms) == 1
    assert atoms[0][Keyword("confidence")] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# REQ-CONFIDENCE-044: verdict_to_qa splits into critical + advisory arrays
# ---------------------------------------------------------------------------


def test_advisory_defects_routed_to_separate_array(tmp_path: Path) -> None:
    from scripts._edn_reader import Keyword
    from scripts._io import write_edn_file

    verdict = tmp_path / "verdict.edn"
    write_edn_file(
        verdict,
        {
            Keyword("version"): 1,
            Keyword("verdict"): Keyword("unsat"),
            Keyword("core"): ["c-hi", "c-lo"],
            Keyword("explanation"): "two defects, one each side",
            Keyword("verified-count"): 5,
            Keyword("defects"): [
                {
                    Keyword("id"): "d-high",
                    Keyword("severity"): Keyword("critical"),
                    Keyword("chain"): [
                        {Keyword("id"): "c-hi", Keyword("confidence"): 0.9},
                    ],
                },
                {
                    Keyword("id"): "d-low",
                    Keyword("severity"): Keyword("critical"),
                    Keyword("chain"): [
                        {Keyword("id"): "c-lo", Keyword("confidence"): 0.2},
                    ],
                },
            ],
        },
    )
    out = tmp_path / "verification-defects.json"
    translate(verdict, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "critical_defects" in payload
    assert "advisory_defects" in payload
    crit_ids = [d["id"] for d in payload["critical_defects"]]
    adv_ids = [d["id"] for d in payload["advisory_defects"]]
    assert "d-high" in crit_ids
    assert "d-low" in adv_ids
    assert "verdict_confidence" in payload


def test_verdict_with_no_defects_emits_empty_arrays_and_full_confidence(
    tmp_path: Path,
) -> None:
    from scripts._edn_reader import Keyword
    from scripts._io import write_edn_file

    verdict = tmp_path / "verdict.edn"
    write_edn_file(
        verdict,
        {
            Keyword("version"): 1,
            Keyword("verdict"): Keyword("sat"),
            Keyword("core"): [],
            Keyword("explanation"): "",
            Keyword("verified-count"): 11,
        },
    )
    out = tmp_path / "verification-defects.json"
    translate(verdict, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["critical_defects"] == []
    assert payload["advisory_defects"] == []
    assert payload["verdict_confidence"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# REQ-CONFIDENCE-045: three-chain regression
# ---------------------------------------------------------------------------


def test_confidence_propagation_three_chains(monkeypatch):
    """All three branches of the downgrade rule in one fixture.

    (a) all atoms >= 0.9 — severity unchanged, defect-confidence = min.
    (b) mixed 0.95 / 0.4 — severity unchanged (one anchor exceeds T),
        defect-confidence = 0.4.
    (c) all atoms < 0.5  — severity downgraded to :advisory.
    """
    monkeypatch.setenv("VERIFIER_CONFIDENCE_THRESHOLD", "0.5")
    chains = {
        "a": [
            {"id": "c1", "confidence": 0.95},
            {"id": "c2", "confidence": 0.91},
            {"id": "c3", "confidence": 0.99},
        ],
        "b": [
            {"id": "c4", "confidence": 0.95},
            {"id": "c5", "confidence": 0.4},
        ],
        "c": [
            {"id": "c6", "confidence": 0.3},
            {"id": "c7", "confidence": 0.45},
        ],
    }
    results = {}
    for tag, chain in chains.items():
        dc = compute_defect_confidence(chain)
        # Attach the chain so the downgrade rule can see the per-atom
        # confidences (a single anchor >= T is enough to preserve severity).
        defect = {
            "severity": "critical",
            "defect_confidence": dc,
            "chain": chain,
        }
        apply_confidence_downgrade(defect)
        results[tag] = (dc, defect["severity"])

    assert results["a"] == (pytest.approx(0.91), "critical")
    assert results["b"] == (pytest.approx(0.4), "critical")
    assert results["c"] == (pytest.approx(0.3), "advisory")
