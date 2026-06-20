"""Advisory analogy-mapping scorer: a recurring concrete base-domain anchor + a
mapping cue across >=2 sentences (structure-mapping intuition, not keyword spotting)."""
from __future__ import annotations
import re
from collections import Counter

from scripts.text_util import iter_spacy_sentences
from scripts.concreteness import load_concreteness, conc

_VERY_HIGH = 4.5
_MAP_CUE = re.compile(
    r"\b(like|as if|as though|works? like|behaves? like|acts? like|functions? as|"
    r"think (?:of|about)|imagine|picture|hides?|trades?|reveals?|mirrors?|seals?)\b")


def score_text(text: str) -> dict:
    table = load_concreteness()
    spans = iter_spacy_sentences(text)
    anchor_sentences: Counter = Counter()
    has_cue = False
    for s in spans:
        if _MAP_CUE.search(s.text.lower()):
            has_cue = True
        seen = set()
        for t in s:
            if t.pos_ in ("NOUN", "PROPN"):
                c = conc(t.text, table)
                if c is not None and c >= _VERY_HIGH:
                    seen.add(t.text.lower())
        for w in seen:
            anchor_sentences[w] += 1
    recurring = [w for w, n in anchor_sentences.items() if n >= 2]
    present = bool(recurring) and has_cue
    findings = [{"base_anchor": w, "sentences": anchor_sentences[w]} for w in recurring] if present else []
    return {"signal": "analogy_mapping", "score": 1.0 if present else 0.0, "findings": findings}


def score(sentences, register, profile) -> dict:
    text = " ".join(s.text for s in sentences)
    return score_text(text)
