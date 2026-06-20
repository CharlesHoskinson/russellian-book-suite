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

    counts = Counter(tokens)

    vocab = list(freq_map.keys())
    # H-07: normalize the sample over IN-VOCAB tokens, not the full token count.
    # The profile frequencies are relative over its own vocabulary; dividing the
    # sample by len(tokens) (which includes out-of-vocab words) made the delta
    # drift as OOV padding grew. Counting only vocab tokens puts both
    # distributions on the same denominator, so OOV words don't move the score.
    in_vocab_total = sum(counts.get(w, 0) for w in vocab)
    if in_vocab_total == 0:
        return 0.0
    sample_freqs = [counts.get(w, 0) / in_vocab_total for w in vocab]
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
