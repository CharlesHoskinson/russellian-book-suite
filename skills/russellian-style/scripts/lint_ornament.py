"""Ornament linter: flags purple-prose markers that distinguish decorative from lively.

Pure stdlib + re. Imports nothing from lint_common (which loads spaCy at module top)
so this module loads and runs under the CI [ci] extra without the spaCy model.

Quoted spans (double-quoted, curly-quoted, and markdown blockquotes) are removed
before scanning so the linter does not penalize quoting or discussing ornate sources.
The strip is per-line for double/curly quotes (an unmatched opening quote that spans
paragraphs is not detected); markdown blockquote lines (`>`) are dropped wholesale.
The ``strip_quotes`` helper is exposed publicly so sibling linters (e.g.,
``lint_humanity_token_closers``) reuse it without copy-paste.

Each match emits one finding so ``len(lint_ornament(path))`` measures total ornament
instances — the value ``voice_eval._signals`` consumes via per-1000 density.
Severity is advisory; the tier records internal strength for the report only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


_ARCHAIC = re.compile(
    r"\b(o'er|'tis|'twas|thee|thou|thy|thine|doth|hath|ere|'neath|'gainst|nay)\b",
    re.IGNORECASE,
)

# Sentence-initial "O Reader, ..." or "O Time! ...": the addressee must be followed
# by a comma or exclamation, which is the apostrophe-trope pattern. This excludes
# technical terms like "O Ring" (no following comma/exclamation).
_APOSTROPHE = re.compile(r"(?:^|[.!?]\s+)O[, ]+[A-Z][a-z]+\s*[,!]")

# Closed list of amplifying adverbs paired with already-strong verbs. Using a closed
# list (rather than ``\w+ly``) avoids false positives on nouns and proper nouns that
# happen to end in "ly" — "gully roared", "family roared", "Italy blazed".
_AMPLIFIER_ADVERBS = (
    "loudly", "quietly", "softly", "harshly", "fiercely", "ferociously",
    "mightily", "savagely", "wildly", "frantically", "hastily", "rapidly",
    "swiftly", "deeply", "profoundly", "suddenly", "abruptly", "violently",
    "intensely", "furiously",
)
_STRONG_VERBS = (
    "roared", "shouted", "whispered", "screamed", "blazed", "raced",
    "sprinted", "glared", "thundered", "bellowed",
)
_ADVERB_STRONG_VERB = re.compile(
    r"\b(" + "|".join(_AMPLIFIER_ADVERBS) + r")\s+(" + "|".join(_STRONG_VERBS) + r")\b",
    re.IGNORECASE,
)

_EMOTION_WORDS = (
    "sorrow", "grief", "despair", "longing", "rapture", "melancholy",
    "anguish", "yearning", "woe",
)
# Bare nominal use; tolerate end-of-string so a file that does not end with a newline
# does not silently miss a trailing emotion word.
_EMOTION_RE = re.compile(
    r"(?:^|[\s,;])(" + "|".join(_EMOTION_WORDS) + r")(?=[\s,.;!?]|$)",
    re.IGNORECASE,
)

_EVALUATIVE = (
    "beautiful", "lovely", "gorgeous", "exquisite", "magnificent", "glorious",
    "radiant", "dazzling", "sublime", "delicate", "tender", "wondrous", "ethereal",
)
# Bridge between adjacent evaluative adjectives must NOT cross a line — otherwise the
# pattern fires across sentence boundaries when a line happens to start with an
# evaluative word ("radiant\nTender treatment ...").
_ADJ_STACK = re.compile(
    r"\b(" + "|".join(_EVALUATIVE) + r")\b[, ]+(?:and\s+)?\b("
    + "|".join(_EVALUATIVE) + r")\b",
    re.IGNORECASE,
)

# "the storm raged, as if in sympathy / protest / grief / sorrow / anger / joy"
_NATURE_MOOD = re.compile(
    r"\bas if (?:in|the)\b[^.!?]{0,40}\b(sympathy|protest|grief|sorrow|anger|joy)\b",
    re.IGNORECASE,
)


# (marker, compiled-regex, tier). Tier is internal strength for reports; severity
# stays advisory regardless (REQ-VOICE-015).
_MARKERS: tuple[tuple[str, "re.Pattern[str]", str], ...] = (
    ("archaic_diction", _ARCHAIC, "important"),
    ("apostrophe", _APOSTROPHE, "important"),
    ("adverb_amplified_verb", _ADVERB_STRONG_VERB, "advisory"),
    ("abstract_emotion_word", _EMOTION_RE, "advisory"),
    ("adjective_stacking", _ADJ_STACK, "advisory"),
    ("nature_mirrors_mood", _NATURE_MOOD, "advisory"),
)


def strip_quotes(text: str) -> str:
    # Per-line strip: double-quoted spans, curly-quoted spans, blockquote lines.
    text = re.sub(r'"[^"\n]*"', " ", text)
    text = re.sub(u"“[^”\n]*”", " ", text)
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))
    return text


def lint_ornament(path: Path) -> list[dict]:
    """Return one advisory finding per ornament-marker match. Quoted spans are excluded.

    ``len(lint_ornament(path))`` is the total ornament instance count — what
    ``voice_eval._signals`` consumes as a per-1000-word density.
    """
    text = strip_quotes(Path(path).read_text(encoding="utf-8"))
    findings: list[dict] = []
    for marker, pattern, tier in _MARKERS:
        for _ in pattern.finditer(text):
            findings.append({
                "rule": "ornament",
                "marker": marker,
                "tier": tier,
                "severity": "advisory",
            })
    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_ornament(Path(sys.argv[1])), indent=2))
