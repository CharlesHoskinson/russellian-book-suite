"""Chassis-uniformity linter: four signals catching paragraph-level monotony.

Pure stdlib + ``re`` + ``math`` + ``collections.Counter``. Reuses
``classify_paragraph`` (stdlib) and ``lint_humanity_token_closers``'s closer-gate
predicate. Imports nothing from ``lint_common`` (which loads spaCy at module top)
so this module runs under the CI ``[ci]`` extra without the spaCy English model.

The first-draft ``lint_shape_variance`` operated on ``classify_paragraph``'s
surface shapes with a single 5-of-6 dominance check. Two QA-pass failure modes
were named: (1) the fact-→-pivot-→-aphorism chassis can wear any of the seven
surface costumes, so single-signal shape dominance misses it; (2)
``classify_paragraph`` falls back to ``assertion_justification`` on any paragraph
without explicit discourse markers, producing false-positive saturation on
sparse-marker prose (e.g., Didion).

The rebuilt linter addresses both with four independent signals, returning the
union. Marker-hit shape dominance ignores the fallback shapes
(``assertion_only``, ``assertion_justification``), eliminating failure mode 2.
The closer-density signal catches chassis monotony even when surface shapes
vary, addressing failure mode 1.

All findings are advisory; tier records internal strength.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from scripts.lint_paragraph_motion import classify_paragraph
from scripts.lint_humanity_token_closers import (
    _closing_sentence,
    _is_humanity_token_closer,
)


_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")

# classify_paragraph's seven shapes split into marker-hit (an explicit cue
# matched) and fallback (no cue matched; default by sentence count).
_FALLBACK_SHAPES = frozenset({"assertion_only", "assertion_justification"})
_MARKER_HIT_SHAPES = frozenset({
    "question_answer", "concession_turn", "contrast",
    "example_inference", "definition_by_pressure",
})

# Signal calibration constants.
_WINDOW_SIZE = 5
_WINDOW_DOMINANCE_THRESHOLD = 3  # 3 of 5 = 60%
_STREAK_THRESHOLD = 3            # ≥3 consecutive same shape
_ENTROPY_THRESHOLD = 1.5         # bits; max over 7-shape taxonomy is log2(7) ≈ 2.81
_CLOSER_CONCENTRATION_THRESHOLD = 0.5
_CLOSER_MIN_PARAGRAPHS = 8


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]


def _shapes(paragraphs: list[str]) -> list[str]:
    return [classify_paragraph(p) for p in paragraphs]


def _shape_entropy(shapes: list[str]) -> float:
    """Shannon entropy in bits of the shape sequence; 0.0 for empty."""
    if not shapes:
        return 0.0
    counts = Counter(shapes)
    n = len(shapes)
    h = 0.0
    for c in counts.values():
        p = c / n
        h -= p * math.log2(p)
    return h


def _streak_findings(shapes: list[str]) -> list[dict]:
    findings: list[dict] = []
    i = 0
    while i < len(shapes):
        j = i
        while j + 1 < len(shapes) and shapes[j + 1] == shapes[i]:
            j += 1
        run_length = j - i + 1
        if run_length >= _STREAK_THRESHOLD:
            findings.append({
                "rule": "chassis-uniformity",
                "signal": "streak",
                "shape": shapes[i],
                "start_paragraph": i,
                "run_length": run_length,
                "tier": "important" if run_length >= 4 else "advisory",
                "severity": "advisory",
            })
        i = j + 1
    return findings


def _marker_dominance_findings(shapes: list[str]) -> list[dict]:
    findings: list[dict] = []
    if len(shapes) < _WINDOW_SIZE:
        return findings
    seen_windows: set[tuple[int, str]] = set()
    for start in range(len(shapes) - _WINDOW_SIZE + 1):
        window = shapes[start:start + _WINDOW_SIZE]
        for shape, count in Counter(window).items():
            if shape in _FALLBACK_SHAPES:
                continue
            if count >= _WINDOW_DOMINANCE_THRESHOLD:
                key = (start, shape)
                if key in seen_windows:
                    continue
                seen_windows.add(key)
                findings.append({
                    "rule": "chassis-uniformity",
                    "signal": "marker_dominance",
                    "shape": shape,
                    "start_paragraph": start,
                    "window_size": _WINDOW_SIZE,
                    "count_in_window": count,
                    "tier": "important" if count >= 4 else "advisory",
                    "severity": "advisory",
                })
    return findings


def _entropy_finding(shapes: list[str]) -> list[dict]:
    if len(shapes) < _CLOSER_MIN_PARAGRAPHS:
        # Entropy on a very short document is uninformative; suppress.
        return []
    h = _shape_entropy(shapes)
    if h < _ENTROPY_THRESHOLD:
        return [{
            "rule": "chassis-uniformity",
            "signal": "entropy",
            "entropy": round(h, 3),
            "threshold": _ENTROPY_THRESHOLD,
            "n_paragraphs": len(shapes),
            "tier": "important" if h < 1.0 else "advisory",
            "severity": "advisory",
        }]
    return []


def _closer_concentration_finding(paragraphs: list[str]) -> list[dict]:
    if len(paragraphs) < _CLOSER_MIN_PARAGRAPHS:
        return []
    closer_count = sum(
        1 for p in paragraphs
        if _is_humanity_token_closer(_closing_sentence(p))
    )
    proportion = closer_count / len(paragraphs)
    if proportion >= _CLOSER_CONCENTRATION_THRESHOLD:
        return [{
            "rule": "chassis-uniformity",
            "signal": "closer_concentration",
            "closer_proportion": round(proportion, 3),
            "closer_count": closer_count,
            "n_paragraphs": len(paragraphs),
            "tier": "important" if proportion >= 0.7 else "advisory",
            "severity": "advisory",
        }]
    return []


def lint_chassis_uniformity(path: Path) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    paragraphs = _paragraphs(text)
    shapes = _shapes(paragraphs)
    return (
        _streak_findings(shapes)
        + _marker_dominance_findings(shapes)
        + _entropy_finding(shapes)
        + _closer_concentration_finding(paragraphs)
    )


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_chassis_uniformity(Path(sys.argv[1])), indent=2))
