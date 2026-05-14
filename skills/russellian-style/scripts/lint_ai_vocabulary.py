"""AI-vocabulary linter: humanizer catalog + Russell-specific overlay.

Loads humanizer's 24-pattern catalog via sibling_skills when available;
runs the Russell-specific supplement (assets/ai-vocabulary-supplement.json)
in all cases. Reports one finding per detected occurrence with pattern_id,
phrase, and line.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .lint_common import iter_sentences, load_markdown
from .sibling_skills import SiblingNotFoundError, humanizer_available, load_humanizer_catalog


SUPPLEMENT_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "ai-vocabulary-supplement.json"
)


def load_supplement() -> dict:
    return json.loads(SUPPLEMENT_PATH.read_text(encoding="utf-8"))


def _word_boundary_pattern(phrases: list[str]) -> re.Pattern:
    escaped = [re.escape(p) for p in sorted(phrases, key=len, reverse=True)]
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", flags=re.IGNORECASE)


def _sentence_starts_with(sentence: str, phrases: list[str]) -> str | None:
    head = sentence.strip().lstrip("*_>#- ").lower()
    for p in phrases:
        if head.startswith(p.lower() + " ") or head.startswith(p.lower() + ","):
            return p
    return None


def lint_ai_vocabulary(path: Path) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []

    supplement = load_supplement()
    patterns_by_id = {p["id"]: p for p in supplement["patterns"]}

    # All vitality linters advisory in v1; tier records the internal
    # strength of the finding for the report.
    fc = patterns_by_id["false_certainty"]
    fc_re = _word_boundary_pattern(fc["phrases"])
    for sentence in iter_sentences(text):
        for m in fc_re.finditer(sentence.text):
            findings.append({
                "rule": "ai-vocabulary",
                "pattern_id": "false_certainty",
                "phrase": m.group(1),
                "sentence": sentence.text,
                "line": getattr(sentence, "line", 0),
                "tier": "important",
                "severity": "advisory",
            })

    ma = patterns_by_id["magic_adverb"]
    ma_re = _word_boundary_pattern(ma["words"])
    for sentence in iter_sentences(text):
        for m in ma_re.finditer(sentence.text):
            findings.append({
                "rule": "ai-vocabulary",
                "pattern_id": "magic_adverb",
                "phrase": m.group(1),
                "sentence": sentence.text,
                "line": getattr(sentence, "line", 0),
                "tier": "important",
                "severity": "advisory",
            })

    ta = patterns_by_id["transition_adverb_starter"]
    for sentence in iter_sentences(text):
        hit = _sentence_starts_with(sentence.text, ta["phrases"])
        if hit:
            findings.append({
                "rule": "ai-vocabulary",
                "pattern_id": "transition_adverb_starter",
                "phrase": hit,
                "sentence": sentence.text,
                "line": getattr(sentence, "line", 0),
                "tier": "important",
                "severity": "advisory",
            })

    # Note: sweeping_abstraction_subject requires a dependency parser; deferred.

    if humanizer_available():
        try:
            catalog = load_humanizer_catalog()
        except SiblingNotFoundError:
            catalog = {}
        for cat_id, phrases in catalog.items():
            if not isinstance(phrases, list) or not phrases:
                continue
            cat_re = _word_boundary_pattern(
                [str(p) for p in phrases if isinstance(p, str)]
            )
            for sentence in iter_sentences(text):
                for m in cat_re.finditer(sentence.text):
                    findings.append({
                        "rule": "ai-vocabulary",
                        "pattern_id": f"humanizer:{cat_id}",
                        "phrase": m.group(1),
                        "sentence": sentence.text,
                        "line": getattr(sentence, "line", 0),
                        "tier": "important",
                        "severity": "advisory",
                    })

    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_ai_vocabulary(Path(sys.argv[1])), indent=2))
