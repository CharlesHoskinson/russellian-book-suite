"""Build the three doctored fixtures from claims_clean.jsonl.

Each doctored fixture is the clean ledger plus a small handful of injected
tampered claims that trip exactly one constraint class:

  - claims_doctored_low_n.jsonl                : n=3 trial (trips D40)
  - claims_doctored_p_value_drift.jsonl        : p=0.74 trial (trips D41)
  - claims_doctored_adverse_above_efficacy.jsonl: adverse 87% with efficacy 22% (trips D42)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "fixtures" / "claims_clean.jsonl"
OUT_DIR = ROOT / "fixtures"


def load_clean() -> list[dict]:
    rows: list[dict] = []
    with CLEAN.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_fixture(name: str, rows: list[dict]) -> None:
    out = OUT_DIR / name
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False))
            fh.write("\n")
    print(f"[doctored] wrote {name}: {len(rows)} claims")


def make_synthetic(claim_id: str, text: str, doc_locator: str) -> dict:
    return {
        "claim_id": claim_id,
        "claim_type": "fact",
        "canonical_text": text,
        "status": "verified",
        "confidence": 1.0,
        "source_spans": [
            {"doc_id": "adsc-doctored-injection", "locator_text": doc_locator}
        ],
        "supports_chapters": [],
    }


def split_clean_fixtures(clean: list[dict]) -> None:
    """Split the full clean ledger into 5 named partitions.

    REQ-CORPUS-042 demands at least 5 clean fixtures. We partition the 1852
    quantitative-claim ledger into five overlapping views (intro/exec,
    knee-OA, Crohn's, autoimmune+misc, regulatory+global) so each "clean"
    file is itself a valid claim set the framework can verify. Partitioning
    by chapter heuristics rather than round-robin keeps each clean fixture
    semantically coherent.
    """
    # Heuristic anchors. If the claim text references the anchor, route it
    # to that bucket; else falls through to the catch-all.
    buckets = {
        "claims_clean_intro.jsonl": [],
        "claims_clean_knee_oa.jsonl": [],
        "claims_clean_crohns.jsonl": [],
        "claims_clean_cardiac_neuro.jsonl": [],
        "claims_clean_regulatory.jsonl": [],
    }
    routes = [
        ("claims_clean_knee_oa.jsonl", ["knee", "osteoarthritis", "OA"]),
        ("claims_clean_crohns.jsonl", ["Crohn", "fistula", "alofisel", "ADMIRE"]),
        (
            "claims_clean_cardiac_neuro.jsonl",
            ["cardiac", "stroke", "neurolog", "Parkinson", "MS ", "spinal", "TREASURE"],
        ),
        (
            "claims_clean_regulatory.jsonl",
            [
                "FDA",
                "regulator",
                "approval",
                "Wyoming",
                "offshore",
                "21 CFR",
                "EMA",
            ],
        ),
    ]
    for c in clean:
        text = c["canonical_text"]
        placed = False
        for name, anchors in routes:
            if any(a.lower() in text.lower() for a in anchors):
                buckets[name].append(c)
                placed = True
                break
        if not placed:
            buckets["claims_clean_intro.jsonl"].append(c)
    for name, rows in buckets.items():
        write_fixture(name, rows)


def main() -> int:
    clean = load_clean()
    split_clean_fixtures(clean)

    # D40: n < 10
    low_n = clean + [
        make_synthetic(
            "adsc-doctored-low-n-001",
            "The pilot trial enrolled patients with severe knee OA at a "
            "single site (n=3) and reported initial safety signals.",
            "doctored: low cohort size",
        ),
        make_synthetic(
            "adsc-doctored-low-n-002",
            "Phase 0 dose-finding cohort (n=5) over a 12-week window.",
            "doctored: low cohort size",
        ),
    ]
    write_fixture("claims_doctored_low_n.jsonl", low_n)

    # D41: p > 0.05
    p_drift = clean + [
        make_synthetic(
            "adsc-doctored-pvalue-001",
            "The primary efficacy comparison did not reach significance "
            "(p = 0.74) on the change-from-baseline outcome.",
            "doctored: non-significant p",
        ),
        make_synthetic(
            "adsc-doctored-pvalue-002",
            "Subgroup analysis on the responders arm: p = 0.31, n=42.",
            "doctored: above-threshold p",
        ),
    ]
    write_fixture("claims_doctored_p_value_drift.jsonl", p_drift)

    # D42: adverse > efficacy. Inject ONE trial whose AE rate > efficacy.
    adv_high = clean + [
        make_synthetic(
            "adsc-doctored-adverse-001",
            "Of the 60 enrolled, 87% adverse events were reported across "
            "the trial period.",
            "doctored: AE 87%",
        ),
        make_synthetic(
            "adsc-doctored-efficacy-001",
            "The response rate was 22% on the primary endpoint.",
            "doctored: efficacy 22%",
        ),
    ]
    write_fixture("claims_doctored_adverse_above_efficacy.jsonl", adv_high)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
