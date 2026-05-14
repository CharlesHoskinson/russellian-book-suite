"""Burstiness linter: Fano factor + AI-band proportion.

PDF-grounded targets ("AI Prose: From Terseness to Cadence", §3):
  - AI prose: mean 14.38 words/sentence; tight band 12.33-17.64.
  - Human prose: mean 19.28; range 15.67-25.60; high Fano factor.
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, pvariance

from .lint_common import iter_sentences, load_markdown


AI_BAND = (12, 17)


def lint_burstiness(path: Path) -> list[dict]:
    text = load_markdown(path)
    lengths = [len(s.text.split()) for s in iter_sentences(text)]
    if len(lengths) < 2:
        return []
    mu = mean(lengths)
    sigma2 = pvariance(lengths)
    fano = sigma2 / mu if mu > 0 else 0.0
    in_band = sum(1 for n in lengths if AI_BAND[0] <= n <= AI_BAND[1])
    in_band_prop = in_band / len(lengths)

    tier = _tier(fano, in_band_prop)
    if tier == "pass":
        return []
    # All new vitality linters land at advisory in v1 per the design spec.
    # `tier` records the internal strength of the finding for the report;
    # severity stays advisory until the promotion follow-up spec calibrates
    # the linters against persona findings.
    return [{
        "rule": "burstiness",
        "fano_factor": round(fano, 3),
        "mean_words_per_sentence": round(mu, 2),
        "in_band_proportion": round(in_band_prop, 3),
        "sentence_count": len(lengths),
        "tier": tier,
        "severity": "advisory",
    }]


def _tier(fano: float, in_band_prop: float) -> str:
    if fano < 0.3 or in_band_prop > 0.85:
        return "critical"
    if fano < 0.5:
        return "important"
    if fano < 0.7:
        return "advisory"
    return "pass"


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_burstiness(Path(sys.argv[1])), indent=2))
