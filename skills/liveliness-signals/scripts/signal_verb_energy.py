"""Advisory verb-energy scorer: lexical-verb density + light-verb-construction flags.

Targets light-verb + event-noun constructions (make a proposal), not all
nominalizations (cmp-lg/9503010). Lemmatizer is off, so light verbs are matched
by an inflected text set.
"""
from __future__ import annotations
import re

from scripts.text_util import iter_spacy_sentences

_LIGHT_VERBS = {
    "make", "makes", "made", "making",
    "have", "has", "had", "having",
    "give", "gives", "gave", "giving",
    "take", "takes", "took", "taking",
    "do", "does", "did", "doing",
    "conduct", "conducts", "conducted",
    "perform", "performs", "performed",
    "provide", "provides", "provided",
}
# Deverbal event-noun suffixes (cmp-lg/9503010). -al/-ure are deverbal (proposal,
# approval, failure, departure); -ness/-ship are state/relational, NOT events, excluded.
_EVENT_NOUN = re.compile(r"(tion|ment|ance|ence|sion|ity|ing|al|ure)$")


def score_text(text: str) -> dict:
    spans = iter_spacy_sentences(text)
    content = 0
    lexical_verbs = 0
    findings: list[dict] = []
    for sent in spans:
        for t in sent:
            if t.is_alpha:
                content += 1
                if t.pos_ == "VERB":
                    lexical_verbs += 1
            # light-verb construction: light verb governing an event-noun dobj
            if t.pos_ == "VERB" and t.text.lower() in _LIGHT_VERBS:
                for child in t.children:
                    if child.dep_ == "dobj" and child.pos_ == "NOUN" and _EVENT_NOUN.search(child.text.lower()):
                        findings.append({"construction": f"{t.text.lower()} {child.text.lower()}",
                                        "line": sent.start})
    score = lexical_verbs / content if content else 0.0
    return {"signal": "verb_energy", "score": round(score, 4),
            "lexical_verb_density": round(score, 4), "findings": findings}


def score(sentences, register, profile) -> dict:
    # Harness passes Plan-3a Sentence objects (no deps); re-derive from their text.
    text = " ".join(s.text for s in sentences)
    return score_text(text)
