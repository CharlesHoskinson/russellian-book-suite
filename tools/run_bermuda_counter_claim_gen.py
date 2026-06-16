"""Generate bermuda counter-claims using a fixed in-line rival corpus.

Mirrors generate_counter_claims.generate_for_claim with an llm_call that
returns pre-computed JSON for each known load-bearing claim. Single-use:
do not generalize.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

# Make book-knowledge scripts importable.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "book-knowledge"))

from scripts.generate_counter_claims import (  # noqa: E402
    generate_for_claim, _latest_claim_record,
)

WS = REPO / "examples" / "bermuda-manual"

RIVALS = {
    # geography-shapes-economy
    # Claim: Bermuda's mid-Atlantic position, lack of arable land, reef shelter,
    # and tropical climate TOGETHER explain the economic structure — from the
    # seventeenth-century salt trade through tourism to today's reinsurance sector.
    "clm-2026-000002": [
        {
            "text": (
                "Bermuda's emergence as the world's leading captive-insurance and "
                "reinsurance centre is explained by the 1953 Companies Act and its "
                "successive exempted-company amendments, not by the island's physical "
                "geography, which offers no locational advantage over other small "
                "jurisdictions that never developed comparable financial sectors."
            ),
            "disagreement_vector": "mechanism",
        },
        {
            "text": (
                "The seventeenth-century Bermuda salt trade and the twentieth-century "
                "reinsurance industry share no continuous causal chain — the former "
                "collapsed by 1800 and the latter arose entirely from post-Hurricane "
                "Hugo and Andrew capital flight in the 1980s-1990s, making the "
                "claimed geographic continuity a retrospective illusion."
            ),
            "disagreement_vector": "time_period",
        },
        {
            "text": (
                "Bermuda's reef-sheltered harbours and mid-Atlantic position explain "
                "the shipping and naval economy of the colonial period but not the "
                "contemporary economy, which is driven by tax and regulatory arbitrage "
                "available to any sovereign or quasi-sovereign jurisdiction regardless "
                "of physical location."
            ),
            "disagreement_vector": "scope",
        },
    ],

    # history-shapes-government
    # Claim: The 1968 Constitution Order is the founding instrument of contemporary
    # self-government; the political settlement traces back through 1834 emancipation,
    # slavery, and the colonial era.
    "clm-2026-000003": [
        {
            "text": (
                "The 1995 independence referendum, in which 73 percent of Bermudian "
                "voters rejected sovereignty, was a more constitutively determining "
                "moment for contemporary self-government than the 1968 Constitution "
                "Order, because it fixed the permanent territorial status that all "
                "subsequent political actors must operate within."
            ),
            "disagreement_vector": "time_period",
        },
        {
            "text": (
                "The political mobilisation that produced the 1968 constitutional "
                "settlement derived primarily from the 1959 Theatre Boycott and the "
                "1965 labour strikes led by the Progressive Labour Party, not from the "
                "long-run logic of the 1834 emancipation, making the post-slavery "
                "lineage a rhetorical frame rather than an operative causal chain."
            ),
            "disagreement_vector": "mechanism",
        },
        {
            "text": (
                "The 1968 Constitution Order entrenched the power of the white "
                "merchant oligarchy through property-franchise residues and the "
                "two-seat constituency system, so the PLP's 1998 electoral victory — "
                "not the 1968 Order itself — is the actual founding moment of "
                "Black-majority political control."
            ),
            "disagreement_vector": "measurement",
        },
    ],

    # institutions
    # Claim: Bermuda College, KEMH, MWI, the ferry/scooter mobility regime are
    # the "lived-experience surface" of deeper economic and constitutional structures.
    "clm-2026-000007": [
        {
            "text": (
                "The King Edward VII Memorial Hospital's chronic underfunding and "
                "structural deficits have forced successive governments to abandon "
                "fiscal priorities, demonstrating that the healthcare institution "
                "operates as an independent fiscal and political constraint rather "
                "than a surface expression of underlying economic structures."
            ),
            "disagreement_vector": "mechanism",
        },
        {
            "text": (
                "The scooter-dominated mobility regime is an artefact of a 1946 "
                "Motor Car Act restriction designed to protect the taxi industry, "
                "a path-dependent regulatory accident that has no systematic "
                "relationship to Bermuda's constitutional or economic architecture."
            ),
            "disagreement_vector": "scope",
        },
        {
            "text": (
                "Bermuda College's establishment in 1974 and its subsequent "
                "community-college model were shaped principally by Caribbean "
                "regional higher-education policy norms and American accreditation "
                "requirements, not by the domestic economic or constitutional "
                "structures the claim treats as the primary determinants."
            ),
            "disagreement_vector": "population",
        },
    ],
}


def _llm_for(cid: str):
    def _call(prompt: str) -> str:
        return json.dumps(RIVALS[cid])
    return _call


def generate(ws: Path = WS) -> dict[str, list[str]]:
    """Generate counter-claims for each RIVALS cid in ``ws``, idempotently.

    H-06: a cid whose latest ledger record already carries counter_claim_ids is
    skipped, so re-running the tool does not append a second set of rivals.
    """
    out: dict[str, list[str]] = {}
    for cid in RIVALS:
        existing = _latest_claim_record(ws, cid)
        if existing and existing.get("counter_claim_ids"):
            print(f"{cid}: already has counter-claims, skipping")
            out[cid] = []
            continue
        ids = generate_for_claim(ws, cid, llm_call=_llm_for(cid))
        print(f"{cid}: generated {len(ids)} counter-claims -> {ids}")
        out[cid] = ids
    return out


def main():
    generate(WS)


if __name__ == "__main__":
    main()
