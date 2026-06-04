"""Flag sentences whose Flesch-Kincaid grade load exceeds the budget."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import iter_sentences, load_markdown

# Flesch-Kincaid grade is computed per sentence. Unavoidable domain nouns
# (segmentation, cryptanalysis, normalization) inflate the syllables-per-word
# term regardless of how plain the syntax is, so a grade-12 cap flags essentially
# every technical sentence. 16 keeps genuinely tangled prose flagged while letting
# warm-but-technical sentences pass.
DEFAULT_MAX_GRADE = 16


def _syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    vowels = re.findall(r"[aeiouy]", w)
    count = len(vowels)
    # consecutive vowel pairs typically form one syllable
    count -= len(re.findall(r"[aeiou][aeiou]", w))
    # 'i' followed by another vowel is two syllables (e.g. intuition, -io-, -ia-)
    count += len(re.findall(r"i[aeiou]", w))
    # silent e at end
    if w.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _fk_grade(words: int, sentences: int, syllables: int) -> float:
    if words == 0 or sentences == 0:
        return 0.0
    return 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59


def lint_reading_grade(path: Path, max_grade: int = DEFAULT_MAX_GRADE) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []
    for sentence in iter_sentences(text):
        words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", sentence.text)
        if len(words) < 6:
            continue  # too short to grade meaningfully
        syl = sum(_syllables(w) for w in words)
        grade = _fk_grade(len(words), 1, syl)
        if grade > max_grade:
            findings.append({
                "rule": "reading-grade",
                "grade": round(grade, 1),
                "sentence": sentence.text,
                "line": sentence.line,
                "col": sentence.col,
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_reading_grade.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_reading_grade(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
