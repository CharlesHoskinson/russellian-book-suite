"""Advisory concrete-anchor scorer: imageability density + reuse-as-anchor bonus."""
from __future__ import annotations
from collections import Counter

from scripts.text_util import iter_spacy_sentences
from scripts.concreteness import load_concreteness, conc

_HIGH = 4.0


def score_text(text: str) -> dict:
    table = load_concreteness()
    spans = iter_spacy_sentences(text)
    noun_scores: list[float] = []
    per_sentence: list[set] = []
    for s in spans:
        anchors = set()
        for t in s:
            if t.pos_ in ("NOUN", "PROPN"):
                c = conc(t.text, table)
                if c is not None:
                    noun_scores.append(c)
                    if c >= _HIGH:
                        anchors.add(t.text.lower())
        per_sentence.append(anchors)
    if not noun_scores:
        return {"signal": "concrete_anchor", "score": 0.0, "ratio": 0.0, "findings": []}
    ratio = sum(1 for c in noun_scores if c >= _HIGH) / len(noun_scores)
    counts = Counter(w for anchors in per_sentence for w in anchors)
    reused = [w for w, n in counts.items() if n >= 2]
    bonus = 0.1 * len(reused)
    findings = [{"anchor": w, "sentences": counts[w]} for w in reused]
    return {"signal": "concrete_anchor", "score": round(min(1.0, ratio + bonus), 4),
            "ratio": round(ratio, 4), "findings": findings}


def score(sentences, register, profile) -> dict:
    text = " ".join(s.text for s in sentences)
    return score_text(text)
