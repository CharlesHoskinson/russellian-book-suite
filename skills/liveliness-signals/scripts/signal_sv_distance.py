"""Advisory subject->verb distance scorer (Gopen-Swan cognitive load)."""
from __future__ import annotations

from scripts.text_util import iter_spacy_sentences

_MAX = 7


def score_text(text: str) -> dict:
    spans = iter_spacy_sentences(text)
    findings: list[dict] = []
    ok = 0
    measured = 0
    for sent in spans:
        root = sent.root
        subj = next((c for c in root.children if c.dep_ == "nsubj"), None)
        if subj is None:
            continue
        measured += 1
        dist = abs(root.i - subj.i)
        if dist > _MAX:
            findings.append({"distance": dist, "subject": subj.text, "verb": root.text, "line": sent.start})
        else:
            ok += 1
    score = ok / measured if measured else 0.0
    return {"signal": "sv_distance", "score": round(score, 4), "measured": measured, "findings": findings}


def score(sentences, register, profile) -> dict:
    text = " ".join(s.text for s in sentences)
    return score_text(text)
