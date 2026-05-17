"""Verify that examples/bermuda-manual/claims/ledger.jsonl carries the four
quantitative claims that exercise the new BookLogic predicates.

REQ-BERMUDA-RULES-018..021"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
LEDGER = REPO_ROOT / "examples" / "bermuda-manual" / "claims" / "ledger.jsonl"


def _all_claims() -> list[dict]:
    rows = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _latest_per_id() -> dict[str, dict]:
    out = {}
    for r in _all_claims():
        cid = r.get("claim_id")
        if cid:
            out[cid] = r
    return out


@pytest.mark.parametrize("claim_id,expected_predicate", [
    ("clm-2026-000011", "population"),
    ("clm-2026-000012", "land-area-km2"),
    ("clm-2026-000013", "gdp-usd-billion"),
    ("clm-2026-000014", "hospital-beds-kemh"),
])
def test_quantitative_claim_present(claim_id: str, expected_predicate: str) -> None:
    latest = _latest_per_id()
    assert claim_id in latest, f"{claim_id} missing from ledger"
    claim = latest[claim_id]
    assert claim["status"] == "verified", \
        f"{claim_id} must be :status verified (got {claim['status']})"
    # The canonical_text must include enough surface so the lift regex matches.
    assert expected_predicate.split("-")[0] in claim["canonical_text"].lower(), \
        f"{claim_id} canonical_text must mention {expected_predicate}"


def test_ledger_append_only_existing_claims_intact() -> None:
    """Existing claim_ids clm-2026-000001 through 000010 must still appear,
    untouched by the append."""
    latest = _latest_per_id()
    for n in range(1, 11):
        cid = f"clm-2026-{n:06d}"
        assert cid in latest, f"existing {cid} missing — append-only broken"
