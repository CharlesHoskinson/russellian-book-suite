# skills/voice-eval/scripts/ballot.py
"""Blind pairwise ballots for the in-session judge (REQ-VEVAL-012).

For each prompt the v1/v2 pair is presented twice with the A/B order swapped. The
``shown`` payload omits the arm so the judge is blind; ``_decode`` maps a filled
verdict's A/B keep back to the real arm. Length-match within ±15% word count.
"""
from __future__ import annotations

VERDICT_FIELDS = (
    "keep", "want_next", "momentum", "clarity",
    "voice_authority", "readability", "trustworthiness", "rationale",
)
ORDINAL_FIELDS = ("momentum", "clarity", "voice_authority", "readability", "trustworthiness")
_LENGTH_TOL = 0.15


def _words(text: str) -> int:
    return len(text.split())


def _length_matched(a: dict, b: dict) -> bool:
    wa, wb = _words(a["text"]), _words(b["text"])
    if wa == 0 or wb == 0:
        return False
    return abs(wa - wb) / max(wa, wb) <= _LENGTH_TOL


def _side(p: dict) -> dict:
    # Carries the arm internally for decoding, but ``shown`` is what the judge sees.
    return {"arm": p["arm"], "shown": {"prompt_id": p["prompt_id"], "text": p["text"]}}


def build_ballots(v1_passages: list[dict], v2_passages: list[dict]) -> list[dict]:
    by_pid_v1 = {p["prompt_id"]: p for p in v1_passages}
    by_pid_v2 = {p["prompt_id"]: p for p in v2_passages}
    ballots = []
    for pid in sorted(set(by_pid_v1) & set(by_pid_v2)):
        v1, v2 = by_pid_v1[pid], by_pid_v2[pid]
        matched = _length_matched(v1, v2)
        # Order 1: A=v1, B=v2 ; Order 2: A=v2, B=v1 (swap).
        for idx, (a, b) in enumerate(((v1, v2), (v2, v1))):
            ballots.append({
                "prompt_id": pid,
                "register": v1["register"],
                "order": idx,
                "length_matched": matched,
                "requires_rationale": True,
                "A": _side(a),
                "B": _side(b),
                "verdict": None,   # filled in-session with VERDICT_FIELDS
            })
    return ballots


def decode_keep(ballot: dict) -> str:
    """Map a filled ballot's 'keep' ('A'|'B') to the real arm ('v1'|'v2')."""
    choice = ballot["verdict"]["keep"]
    return ballot[choice]["arm"]
