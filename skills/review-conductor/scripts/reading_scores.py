"""Reading-council scoring: deterministic anchors, scoring prompt, and median
aggregation into one synthesized reading score. Advisory; no live LLM (the dispatcher
is caller-provided); aggregation and anchors are deterministic and offline.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

_VOWELS = "aeiouy"
DIMENSIONS = ("enjoyment", "flow", "style", "quality")


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text)


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"[.!?]+", text) if s.strip()]


def _syllables(word: str) -> int:
    word = word.lower()
    count, prev_vowel = 0, False
    for ch in word:
        is_vowel = ch in _VOWELS
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def flesch_reading_ease(text: str) -> float:
    words, sentences = _words(text), _sentences(text)
    if not words or not sentences:
        return 0.0
    syllables = sum(_syllables(w) for w in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)
    return round(206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word, 2)


def burstiness(text: str) -> float:
    lengths = [len(_words(s)) for s in _sentences(text)]
    lengths = [n for n in lengths if n > 0]
    if len(lengths) < 2:
        return 0.0
    mean = statistics.mean(lengths)
    if mean == 0:
        return 0.0
    return round(statistics.pstdev(lengths) / mean, 3)


def build_scoring_prompt(rubric_text: str, doc_text: str) -> str:
    return (
        f"{rubric_text}\n\n"
        f"# Document to score\n\n{doc_text}\n\n"
        f"# Task\n"
        f"Score the document on each of the four dimensions — enjoyment, flow, style, "
        f"quality — from 1 to 5 against the rubric above, with one line of justification "
        f"per dimension. Return only the four scores and their one-line justifications."
    )


def _band(flesch: float) -> str:
    if flesch >= 70:
        return "very easy"
    if flesch >= 50:
        return "plain"
    return "demanding"


def _synthesize_verdict(medians: dict, overall: float, flesch: float) -> str:
    best = max(DIMENSIONS, key=lambda d: medians[d])
    worst = min(DIMENSIONS, key=lambda d: medians[d])
    return (
        f"Reads at {overall}/5 overall — strongest on {best} ({medians[best]}), "
        f"weakest on {worst} ({medians[worst]}); {_band(flesch)} readability "
        f"(Flesch {flesch})."
    )


def aggregate_reading_scores(persona_scores: list[dict], text: str) -> dict:
    if not persona_scores:
        raise ValueError("need at least one persona score")
    medians = {d: round(statistics.median([s[d] for s in persona_scores]), 2) for d in DIMENSIONS}
    overall = round(statistics.mean([medians[d] for d in DIMENSIONS]), 2)
    flesch = flesch_reading_ease(text)
    burst = burstiness(text)
    return {
        **medians,
        "overall": overall,
        "deterministic": {"flesch": flesch, "burstiness": burst},
        "verdict": _synthesize_verdict(medians, overall, flesch),
    }


def run_reading_council(doc_text: str, *, dispatcher, rubric_text: str,
                        personas: list[str]) -> dict:
    """Score a document with the injected council dispatcher and synthesize one score.

    `dispatcher(prompt, personas) -> list[dict]` returns one score dict per persona
    (keys: enjoyment, flow, style, quality; an optional `note` is ignored in the output).
    No live LLM call happens here; the dispatcher is caller-provided.
    """
    prompt = build_scoring_prompt(rubric_text, doc_text)
    persona_scores = dispatcher(prompt, personas)
    return aggregate_reading_scores(persona_scores, doc_text)


def write_reading_report(report: dict, out_path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: reading_scores.py <doc.md> <persona-scores.json> [out.json]", file=sys.stderr)
        return 2
    text = Path(argv[1]).read_text(encoding="utf-8", errors="replace")
    scores = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    report = aggregate_reading_scores(scores, text)
    if len(argv) > 3:
        write_reading_report(report, argv[3])
        print(f"wrote {argv[3]}")
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
