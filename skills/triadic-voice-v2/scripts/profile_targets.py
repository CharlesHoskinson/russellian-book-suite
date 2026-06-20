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
    written_hi = min(hi, 45)
    parts = [
        f"Cadence target (derived from spoken-transcript corpus — treat as loose written-prose "
        f"guidance, not a literal rule): vary sentence length, most sentences between {lo:.0f} and "
        f"roughly {written_hi:.0f} words. Alternate short punches with longer unpacking; do NOT write "
        f"{hi:.0f}-word run-on sentences just because the spoken corpus reaches that length.",
        f"Address the reader directly in roughly {t['direct_address_rate'] * 100:.0f}% of sentences.",
    ]
    dm = t["discourse_marker_rate"]
    if dm > 1e-6:
        parts.append(f"Open about 1 sentence in {max(1, round(1 / dm))} with a discourse marker.")
    es = t["example_spacing"]
    if es > 0:
        parts.append(f"Land a concrete example about every {es:.0f} sentences.")
    parts.append(f"Keep the modifier (adjective+adverb) ratio at or below {t['modifier_budget']:.2f}.")
    return " ".join(parts)
