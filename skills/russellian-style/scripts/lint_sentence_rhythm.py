"""Detect rhythm uniformity: runs of N consecutive sentences with identical
word counts (within tolerance) or identical sentence openings.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import iter_sentences, load_markdown, load_rules

FUNCTION_OPENERS = {
    "the", "a", "an", "this", "that", "these", "those",
    "it", "they", "we", "you", "he", "she", "there", "here",
}


def _word_count(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s))


def _first_word(s: str) -> str:
    match = re.match(r"\W*(\w+)", s)
    return match.group(1).lower() if match else ""


def _content_words(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"\b\w+\b", s)}


def _is_drumbeat(run_sents, capper_exists: bool, rules: dict) -> bool:
    """Four conditions (REQ-VOICE-009): shallow opener; progressive (distinct
    remainders); lengths not mechanically identical; capped by a turn within 1-2."""
    opener = _first_word(run_sents[0].text)
    if opener not in FUNCTION_OPENERS:
        return False
    if not capper_exists:
        return False
    counts = [_word_count(s.text) for s in run_sents]
    mu = sum(counts) / len(counts)
    cv = (sum((c - mu) ** 2 for c in counts) / len(counts)) ** 0.5 / mu if mu else 0.0
    if cv <= float(rules.get("drumbeat_min_length_cv", 0.10)):
        return False
    # progressive: average pairwise Jaccard of content words (minus the shared opener) is low
    sets = [_content_words(s.text) - {opener} for s in run_sents]
    pairs = [(i, j) for i in range(len(sets)) for j in range(i + 1, len(sets))]

    def jac(a, b):
        u = a | b
        return len(a & b) / len(u) if u else 0.0

    avg_overlap = sum(jac(sets[i], sets[j]) for i, j in pairs) / len(pairs) if pairs else 0.0
    return avg_overlap < float(rules.get("drumbeat_max_pairwise_overlap", 0.6))


def lint_sentence_rhythm(path: Path, rules: dict | None = None) -> list[dict]:
    text = load_markdown(path)
    if rules is None:
        rules = load_rules()
    min_run = int(rules.get("rhythm_run_min_length", 4))
    tolerance = int(rules.get("rhythm_word_count_tolerance", 3))
    exemption = bool(rules.get("rhythm_drumbeat_exemption", False))

    sentences = list(iter_sentences(text))
    findings: list[dict] = []
    if len(sentences) < min_run:
        return findings

    counts = [_word_count(s.text) for s in sentences]
    firsts = [_first_word(s.text) for s in sentences]

    # Uniform word count run
    i = 0
    while i <= len(counts) - min_run:
        window = counts[i : i + min_run]
        if max(window) - min(window) <= tolerance:
            findings.append({
                "rule": "rhythm-uniform-length",
                "start_line": sentences[i].line,
                "run_length": min_run,
                "word_counts": window,
                "snippet": " ".join(s.text for s in sentences[i : i + min_run])[:400],
            })
            i += min_run
        else:
            i += 1

    # Repeated opening run
    i = 0
    while i < len(firsts):
        run_first = firsts[i]
        if not run_first:
            i += 1
            continue
        j = i + 1
        while j < len(firsts) and firsts[j] == run_first:
            j += 1
        run_len = j - i
        if run_len >= min_run:
            run_sents = sentences[i:j]
            capper_exists = j < len(firsts)
            if exemption and _is_drumbeat(run_sents, capper_exists, rules):
                findings.append({
                    "rule": "parallel-list",
                    "first_word": run_first,
                    "start_line": sentences[i].line,
                    "run_length": run_len,
                    "snippet": " ".join(s.text for s in run_sents)[:400],
                })
            else:
                findings.append({
                    "rule": "rhythm-repeated-opening",
                    "first_word": run_first,
                    "start_line": sentences[i].line,
                    "run_length": run_len,
                    "snippet": " ".join(s.text for s in run_sents)[:400],
                })
            i = j
        else:
            i += 1

    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_sentence_rhythm.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_sentence_rhythm(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
