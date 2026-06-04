"""AI-vocabulary linter: humanizer catalog + Feynman-specific overlay.

Loads humanizer's 24-pattern catalog via sibling_skills when available;
runs the Feynman-specific supplement (assets/ai-vocabulary-supplement.json)
in all cases. Reports one finding per detected occurrence with pattern_id,
phrase, and line.

Integrity-class linter: AI slop is unwanted in any register, including
Feynman's. Ported faithfully from russellian-style with no register changes.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .lint_common import iter_sentences, load_markdown
from .sibling_skills import SiblingNotFoundError, humanizer_available, load_humanizer_catalog


# Concrete actors that exempt a sentence from sweeping_abstraction_subject even
# when the grammatical subject is an abstract head noun.
_CONCRETE_ACTOR_NOUNS = {
    "official", "censor", "philosopher", "worker", "student", "judge",
    "magistrate", "officer", "professor", "physician", "scholar", "tradesman",
    "soldier", "merchant", "scientist", "clerk", "minister", "barrister",
    "author", "reader", "auditor", "critic", "defender",
}


@lru_cache(maxsize=1)
def _nlp_parser():
    import spacy
    return spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])


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

    sa = patterns_by_id.get("sweeping_abstraction_subject")
    if sa is not None:
        head_nouns = {n.lower() for n in sa.get("head_nouns", [])}
        nlp = _nlp_parser()
        for sentence in iter_sentences(text):
            doc = nlp(sentence.text)
            subjects = [t for t in doc if t.dep_ in ("nsubj", "nsubjpass")]
            abstract_subj = next(
                (t for t in subjects if t.lower_ in head_nouns), None
            )
            if abstract_subj is None:
                continue
            concrete_actor = any(
                t.pos_ == "PROPN" or t.lower_ in _CONCRETE_ACTOR_NOUNS
                for t in subjects
            )
            if concrete_actor:
                continue
            findings.append({
                "rule": "ai-vocabulary",
                "pattern_id": "sweeping_abstraction_subject",
                "phrase": abstract_subj.lower_,
                "sentence": sentence.text,
                "line": getattr(sentence, "line", 0),
                "tier": "important",
                "severity": "advisory",
            })

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
