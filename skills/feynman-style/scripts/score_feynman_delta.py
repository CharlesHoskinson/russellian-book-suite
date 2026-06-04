"""Advisory Feynman-similarity score (L1 distance to the Feynman frequency profile).

The score is the mean absolute deviation between the target's word frequencies and
Feynman's reference frequencies over the profile's vocabulary. A low score means the
target's function-word usage resembles Feynman's. Advisory only — it gates nothing.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from scripts.build_delta_profile import _WORD
from scripts.delta_math import manhattan_delta

PROFILE_PATH = Path(__file__).resolve().parent.parent / "assets" / "feynman-delta-profile.json"


def load_profile(path: Path = PROFILE_PATH) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError):
        return {}


def score_text(text: str, profile: dict | None = None) -> float:
    """Return L1 distance between text's word frequencies and the Feynman profile.

    Returns 0.0 if the profile is missing/empty or the text has no tokens.
    """
    if profile is None:
        profile = load_profile()

    freq_map: dict[str, float] = profile.get("frequencies", {})
    if not freq_map:
        return 0.0

    tokens = _WORD.findall(text.lower())
    if not tokens:
        return 0.0

    total = len(tokens)
    counts = Counter(tokens)

    vocab = list(freq_map.keys())
    sample_freqs = [counts.get(w, 0) / total for w in vocab]
    profile_freqs = [freq_map[w] for w in vocab]

    # Build per-word signed differences; manhattan_delta returns mean of |x|,
    # giving the mean absolute deviation (L1 distance) between the two distributions.
    diffs = [s - p for s, p in zip(sample_freqs, profile_freqs)]
    return manhattan_delta(diffs)


def score_file(path, profile_path: Path = PROFILE_PATH) -> dict:
    profile = load_profile(profile_path)
    text = Path(path).read_text(encoding="utf-8")
    delta = round(score_text(text, profile), 6)
    return {
        "metric": "feynman-l1-delta",
        "delta": delta,
        "n_words": len(_WORD.findall(text.lower())),
    }


def main(argv: list[str]) -> int:
    args = list(argv[1:])
    if not args:
        print("usage: score_feynman_delta.py <text-file>", file=sys.stderr)
        return 2
    result = score_file(args[0])
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
