"""Advisory Russell-similarity score (classic Burrows's Delta to the reference profile).

The score is the mean absolute z-score of the target's MFW frequencies against
Russell's per-word mean and standard deviation. A low Delta means the target's
function-word usage sits near Russell's; the verdict compares it to the distribution
of Russell's own per-segment Deltas. Advisory only — it gates nothing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.lint_common import load_markdown
from scripts.delta_math import tokenize, relative_frequencies, zscore, manhattan_delta

PROFILE_PATH = Path(__file__).resolve().parent.parent / "assets" / "russell-delta-profile.json"
MIN_WORDS = 1000


def load_profile(path: Path = PROFILE_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _verdict(delta: float, band: dict) -> str:
    """Three honest bands. p90 alone is too strict (~10% of Russell's own segments
    exceed it); `max` is outlier-inflated. The upper fence is one inter-decile range
    past p90, which separates Russell's own variation from genuinely alien prose."""
    p90 = band["p90"]
    fence = p90 + (p90 - band["p10"])
    if delta <= p90:
        return "within Russell's range"
    if delta <= fence:
        return "at the edge of Russell's range"
    return "outside Russell's range"


def score(text: str, profile: dict, min_words: int = MIN_WORDS) -> dict:
    tokens = tokenize(text)
    freqs = relative_frequencies(tokens, profile["mfw"])
    delta = round(manhattan_delta(zscore(freqs, profile["mean"], profile["stdev"])), 6)
    band = profile["centroid_delta"]
    verdict = _verdict(delta, band)
    return {
        "metric": "russell-burrows-delta",
        "delta": delta,
        "band": {"p10": band["p10"], "p50": band["p50"], "p90": band["p90"]},
        "verdict": verdict,
        "n_words": len(tokens),
        "reliable": len(tokens) >= min_words,
    }


def score_file(path, profile_path: Path = PROFILE_PATH) -> dict:
    return score(load_markdown(Path(path)), load_profile(profile_path))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: score_russell_delta.py <markdown-file>", file=sys.stderr)
        return 2
    print(json.dumps(score_file(argv[1]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
