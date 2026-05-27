"""Advisory Russell-similarity score (Cosine Delta to the reference profile)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean as _mean

from scripts.lint_common import load_markdown
from scripts.delta_math import tokenize, relative_frequencies, zscore, cosine_delta

PROFILE_PATH = Path(__file__).resolve().parent.parent / "assets" / "russell-delta-profile.json"
MIN_WORDS = 1000


def load_profile(path: Path = PROFILE_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def score(text: str, profile: dict, min_words: int = MIN_WORDS) -> dict:
    tokens = tokenize(text)
    freqs = relative_frequencies(tokens, profile["mfw"])
    tz = zscore(freqs, profile["mean"], profile["stdev"])
    deltas = [cosine_delta(tz, s) for s in profile["segments_z"]]
    delta = round(_mean(deltas), 6) if deltas else 1.0
    band = profile["internal_delta"]
    verdict = "within Russell's range" if delta <= band["p90"] else "outside Russell's range"
    return {
        "metric": "russell-cosine-delta",
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
