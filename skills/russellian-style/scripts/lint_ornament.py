"""Ornament linter: flags purple-prose markers that distinguish decorative from lively.

Pure stdlib + re. Imports nothing from lint_common (which loads spaCy at module top)
so this module loads and runs under the CI [ci] extra without the spaCy model.

Quoted spans (double-quoted, curly-quoted, and markdown blockquotes) are removed
before scanning so the linter does not penalize quoting or discussing ornate sources.
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

# "O Reader,", "O, Time" at sentence boundaries. Avoids matching the letter O in
# ordinary words by requiring sentence-initial position and a following capital.
_APOSTROPHE = re.compile(r"(?:^|[.!?]\s+)O[, ]+[A-Z][a-z]")

_STRONG_VERBS = ("roared", "shouted", "whispered", "screamed", "blazed", "raced",
                 "sprinted", "glared", "thundered", "bellowed")
_ADVERB_STRONG_VERB = re.compile(
    r"\b\w+ly\s+(" + "|".join(_STRONG_VERBS) + r")\b", re.IGNORECASE
)

_EMOTION_WORDS = ("sorrow", "grief", "despair", "longing", "rapture", "melancholy",
                  "anguish", "yearning", "woe")
# Match the word in subject/object position (bare nominal use), not in compounds.
_EMOTION_RE = re.compile(
    r"(?:^|[\s,;])(" + "|".join(_EMOTION_WORDS) + r")(?=[\s,.;!?])", re.IGNORECASE
)

_EVALUATIVE = ("beautiful", "lovely", "gorgeous", "exquisite", "magnificent",
               "glorious", "radiant", "dazzling", "sublime", "delicate", "tender",
               "wondrous", "ethereal")
_ADJ_STACK = re.compile(
    r"\b(" + "|".join(_EVALUATIVE) + r")\b[,\s]+(?:and\s+)?\b("
    + "|".join(_EVALUATIVE) + r")\b",
    re.IGNORECASE,
)

# "the storm raged, as if in sympathy / protest / grief / sorrow / anger / joy"
_NATURE_MOOD = re.compile(
    r"\bas if (?:in|the)\b[^.!?]{0,40}\b(sympathy|protest|grief|sorrow|anger|joy)\b",
    re.IGNORECASE,
)


def _strip_quotes(text: str) -> str:
    # Drop double-quoted spans, curly-quoted spans, and markdown blockquote lines.
    text = re.sub(r'"[^"\n]*"', " ", text)
    text = re.sub(r"“[^”\n]*”", " ", text)
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))
    return text


def _tier(marker: str) -> str:
    # "Important" tiers carry to the report; "advisory" stays severity-advisory
    # regardless (REQ-VOICE-015). All vitality linters are advisory in v1.
    if marker in {"archaic_diction", "apostrophe"}:
        return "important"
    return "advisory"


def lint_ornament(path: Path) -> list[dict]:
    raw = Path(path).read_text(encoding="utf-8")
    text = _strip_quotes(raw)
    findings: list[dict] = []

    def _add(marker: str, count: int) -> None:
        if count <= 0:
            return
        findings.append({
            "rule": "ornament",
            "marker": marker,
            "count": count,
            "tier": _tier(marker),
            "severity": "advisory",
        })

    _add("archaic_diction", len(_ARCHAIC.findall(text)))
    _add("apostrophe", len(_APOSTROPHE.findall(text)))
    _add("adverb_amplified_verb", len(_ADVERB_STRONG_VERB.findall(text)))
    _add("abstract_emotion_word", len(_EMOTION_RE.findall(text)))
    _add("adjective_stacking", len(_ADJ_STACK.findall(text)))
    _add("nature_mirrors_mood", len(_NATURE_MOOD.findall(text)))
    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_ornament(Path(sys.argv[1])), indent=2))
