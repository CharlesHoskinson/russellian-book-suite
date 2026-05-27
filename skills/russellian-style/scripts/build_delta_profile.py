"""Build the Russell-Delta reference profile from local cleaned text files.

Network-free. Fetching of public-domain sources is a separate step via
scrapling-fetch; this module only computes statistics.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean as _mean, pstdev

from scripts.delta_math import tokenize, relative_frequencies, zscore, cosine_delta

_START_RE = re.compile(r"\*\*\*\s*START OF.*?\*\*\*", re.IGNORECASE | re.DOTALL)
_END_RE = re.compile(r"\*\*\*\s*END OF", re.IGNORECASE)


def strip_gutenberg(text: str) -> str:
    m = _START_RE.search(text)
    if m:
        text = text[m.end():]
    m = _END_RE.search(text)
    if m:
        text = text[:m.start()]
    return text


def segment_tokens(tokens: list[str], size: int, min_size: int) -> list[list[str]]:
    segs = [tokens[i:i + size] for i in range(0, len(tokens), size)]
    return [s for s in segs if len(s) >= min_size]


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = min(len(sorted_vals) - 1, int(round(p * (len(sorted_vals) - 1))))
    return round(sorted_vals[k], 6)


def build_profile(texts: dict[str, str], n_features: int = 300,
                  segment_words: int = 2500, min_segment: int = 1000) -> dict:
    segments: list[list[str]] = []
    for raw in texts.values():
        toks = tokenize(strip_gutenberg(raw))
        segments.extend(segment_tokens(toks, segment_words, min_segment))
    if len(segments) < 2:
        raise ValueError("need >= 2 segments to build a profile")

    total: Counter[str] = Counter()
    for seg in segments:
        total.update(seg)
    mfw = [w for w, _ in total.most_common(n_features)]

    seg_freqs = [relative_frequencies(seg, mfw) for seg in segments]
    mean = [_mean(col) for col in zip(*seg_freqs)]
    stdev = [pstdev(col) for col in zip(*seg_freqs)]
    segments_z = [zscore(f, mean, stdev) for f in seg_freqs]

    deltas: list[float] = []
    for i in range(len(segments_z)):
        for j in range(i + 1, len(segments_z)):
            deltas.append(cosine_delta(segments_z[i], segments_z[j]))
    deltas.sort()
    internal = {
        "p10": _percentile(deltas, 0.10),
        "p50": _percentile(deltas, 0.50),
        "p90": _percentile(deltas, 0.90),
        "max": round(deltas[-1], 6) if deltas else 0.0,
        "mean": round(_mean(deltas), 6) if deltas else 0.0,
        "count": len(deltas),
    }

    return {
        "version": "0.1.0",
        "method": "cosine-delta",
        "n_features": len(mfw),
        "segment_words": segment_words,
        "tokenizer": "lowercase tokens matching [a-z']+",
        "source_policy": "statistics computed from public-domain Project Gutenberg texts; no source prose stored",
        "reference_ids": sorted(texts.keys()),
        "n_segments": len(segments),
        "mfw": mfw,
        "mean": [round(x, 9) for x in mean],
        "stdev": [round(x, 9) for x in stdev],
        "segments_z": [[round(x, 6) for x in z] for z in segments_z],
        "internal_delta": internal,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def build_from_dir(src_dir: Path, out_path: Path, **kw) -> dict:
    texts = {p.stem: p.read_text(encoding="utf-8", errors="replace")
             for p in sorted(Path(src_dir).glob("*.txt"))}
    profile = build_profile(texts, **kw)
    Path(out_path).write_text(json.dumps(profile, indent=1), encoding="utf-8")
    return profile


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: build_delta_profile.py <src_dir> <out.json>", file=sys.stderr)
        return 2
    p = build_from_dir(Path(argv[1]), Path(argv[2]))
    print(f"profile: {p['n_segments']} segments, {p['n_features']} features, "
          f"internal p50={p['internal_delta']['p50']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
