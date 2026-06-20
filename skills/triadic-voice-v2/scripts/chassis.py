"""The six HFR v2 chassis archetypes and a deterministic rotating selector."""
from __future__ import annotations

CHASSIS = [
    {"name": "objection-decomposition-verdict",
     "beats": ["state a hostile objection plainly", "decompose it into parts", "deliver an exact verdict"],
     "registers": ["polemic", "narrative-editorial"]},
    {"name": "definition-correction-worked-case-consequence",
     "beats": ["correct a wrong definition", "ground it in a worked case", "draw the consequence"],
     "registers": ["technical-exposition", "narrative-editorial"]},
    {"name": "concrete-scene-abstraction-boundary",
     "beats": ["open on a concrete scene", "lift to the abstraction", "name the boundary condition"],
     "registers": ["narrative-editorial", "technical-exposition"]},
    {"name": "false-slogan-causal-account-replacement",
     "beats": ["quote a false slogan", "give the causal account", "state the exact replacement claim"],
     "registers": ["polemic", "narrative-editorial"]},
    {"name": "inverted-funnel",
     "beats": ["Russell open: the unhedged thesis", "Feynman develop: unpack by analogy", "Hoskinson close: candid takeaway"],
     "registers": ["technical-exposition", "polemic"]},
    {"name": "feynman-sandwich",
     "beats": ["Feynman open: drop into a concrete scenario", "Russell core: the exact mechanism", "Feynman close: return to the scene"],
     "registers": ["narrative-editorial", "technical-exposition"]},
]


def select(register: str, rotation: int) -> dict:
    pool = [c for c in CHASSIS if register in c["registers"]] or CHASSIS
    return pool[rotation % len(pool)]
