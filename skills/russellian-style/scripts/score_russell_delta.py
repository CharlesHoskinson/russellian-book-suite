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
    reliable = len(tokens) >= min_words
    # Below the minimum word count the Delta is statistically meaningless, so
    # abstain rather than report a band verdict that reads as authoritative (4.4).
    verdict = _verdict(delta, band) if reliable else "insufficient text to assess"
    return {
        "metric": "russell-burrows-delta",
        "delta": delta,
        "band": {"p10": band["p10"], "p50": band["p50"], "p90": band["p90"]},
        "verdict": verdict,
        "n_words": len(tokens),
        "reliable": reliable,
    }


def diagnose(text: str, profile: dict, top: int = 15) -> dict:
    """Per-word Burrows-Delta contributions: the calibration levers.

    Returns the most-frequent words ranked by how far the target's usage diverges
    from Russell's, with direction. A large positive z means the word is *over-used*
    relative to Russell (e.g. emphatic absolutes like "never"/"cannot"); a large
    negative z means *under-used* (Russell's subordinators "of"/"which"/"but").

    Calibrate by prose moves — more subordination, fewer emphatic absolutes, named
    subjects in place of bare "it" — not by hunting single words. Single-word edits
    can raise the Delta (e.g. cutting an under-used "of"). See the vitality guide.
    """
    tokens = tokenize(text)
    mfw, mean, stdev = profile["mfw"], profile["mean"], profile["stdev"]
    freqs = relative_frequencies(tokens, mfw)
    z = zscore(freqs, mean, stdev)
    rows = [
        {
            "word": w,
            "target_freq": round(f, 5),
            "russell_freq": round(m, 5),
            "z": round(zz, 3),
            "direction": "over-used" if zz > 0 else "under-used",
        }
        for w, f, m, zz in zip(mfw, freqs, mean, z)
    ]
    rows.sort(key=lambda r: abs(r["z"]), reverse=True)
    return {
        "metric": "russell-burrows-delta-diagnosis",
        "delta": round(manhattan_delta(z), 6),
        "n_words": len(tokens),
        "reliable": len(tokens) >= MIN_WORDS,
        "top_divergent": rows[:top],
    }


def score_file(path, profile_path: Path = PROFILE_PATH) -> dict:
    # Lazy import: lint_common does `import spacy` at module load, which fails in
    # environments without spaCy's deps; keep this module import-safe without it.
    from scripts.lint_common import load_markdown
    return score(load_markdown(Path(path)), load_profile(profile_path))


def diagnose_file(path, profile_path: Path = PROFILE_PATH, top: int = 15) -> dict:
    from scripts.lint_common import load_markdown
    return diagnose(load_markdown(Path(path)), load_profile(profile_path), top=top)


def main(argv: list[str]) -> int:
    args = list(argv[1:])
    diag = False
    if args and args[0] == "--diagnose":
        diag, args = True, args[1:]
    if not args:
        print("usage: score_russell_delta.py [--diagnose] <markdown-file>", file=sys.stderr)
        return 2
    result = diagnose_file(args[0]) if diag else score_file(args[0])
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
