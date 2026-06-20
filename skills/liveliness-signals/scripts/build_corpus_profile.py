# skills/liveliness-signals/scripts/build_corpus_profile.py
"""Build assets/hoskinson-style-profile.json from the Hoskinson corpus.

Network-free, deterministic, statistics-only. Register thresholds fall back to the
global profile so a thin register never yields a degenerate corridor.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.corpus import load_corpus, REGISTERS
from scripts.profile_metrics import (
    sentence_lengths, cadence_corridor, diction_device_metrics, modifier_ratios,
)

_SKILL_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CORPUS = _SKILL_ROOT.parent / "russellian-style" / "assets" / "hoskinson-corpus" / "index.json"
_DEFAULT_OUT = _SKILL_ROOT / "assets" / "hoskinson-style-profile.json"


def _modifier_block(texts: list[str]) -> dict:
    ratios = sorted(modifier_ratios(texts))
    def pct(p):
        if not ratios:
            return 0.0
        k = min(len(ratios) - 1, int(round(p * (len(ratios) - 1))))
        return round(float(ratios[k]), 6)
    return {"p50": pct(0.50), "p75": pct(0.75), "p90": pct(0.90), "count": len(ratios)}


def _profile_for(texts: list[str]) -> dict:
    return {"cadence": cadence_corridor(sentence_lengths(texts)),
            "diction": diction_device_metrics(texts),
            "modifier": _modifier_block(texts)}


def build_profile(rows: list[dict], min_per_register: int = 5) -> dict:
    glob = _profile_for([r["text"] for r in rows])
    registers: dict = {}
    for reg in REGISTERS:
        texts = [r["text"] for r in rows if r["register"] == reg]
        if len(texts) >= min_per_register:
            registers[reg] = {"count": len(texts), "fallback": False, **_profile_for(texts)}
        else:
            registers[reg] = {"count": len(texts), "fallback": True,
                              "cadence": glob["cadence"], "diction": glob["diction"],
                              "modifier": glob["modifier"]}
    return {
        "version": "0.1.0",
        "source_policy": "Statistics only; no source prose stored.",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "global": glob,
        "registers": registers,
    }


def main(argv: list[str]) -> int:
    corpus = Path(argv[1]) if len(argv) > 1 else _DEFAULT_CORPUS
    out = Path(argv[2]) if len(argv) > 2 else _DEFAULT_OUT
    rows = load_corpus(corpus)
    profile = build_profile(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(rows)} paragraphs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
