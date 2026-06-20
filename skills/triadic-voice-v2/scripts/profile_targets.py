"""Format per-register corpus statistics into prompt-injectable generation targets."""
from __future__ import annotations
import json
from pathlib import Path

_PROFILE = Path(__file__).resolve().parent.parent.parent / "liveliness-signals" / "assets" / "hoskinson-style-profile.json"


def load_profile() -> dict:
    return json.loads(_PROFILE.read_text(encoding="utf-8"))


def targets(register: str, profile: dict) -> dict:
    reg = profile["registers"][register]
    cad, dic = reg["cadence"], reg["diction"]
    mod = reg.get("modifier", {})
    return {
        "sentence_len_band": (cad["p10"], cad["p90"]),
        "cadence_cv": cad["cv"],
        "discourse_marker_rate": dic["discourse_marker_rate"],
        "direct_address_rate": dic["direct_address_rate"],
        "example_spacing": dic["example_spacing"],
        "modifier_budget": mod.get("p90", 0.25),
    }


def as_prompt(t: dict) -> str:
    lo, hi = t["sentence_len_band"]
    return (
        f"Cadence target: vary sentence length mostly between {lo:.0f} and {hi:.0f} words "
        f"(coefficient of variation near {t['cadence_cv']:.2f} — alternate short punches with longer unpacking). "
        f"Address the reader directly about {t['direct_address_rate']*100:.0f}% of sentences; "
        f"open roughly 1 sentence in {max(1, round(1/ max(t['discourse_marker_rate'],1e-6))) if t['discourse_marker_rate'] else 0} "
        f"with a discourse marker. Land a concrete example about every {t['example_spacing']:.0f} sentences. "
        f"Keep the modifier (adjective+adverb) ratio at or below {t['modifier_budget']:.2f}."
    )
