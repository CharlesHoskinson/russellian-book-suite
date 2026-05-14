"""Concrete-instance-density linter.

Counts named entities (spaCy NER: PERSON, ORG, GPE, DATE, MONEY, ORDINAL,
EVENT, NORP, LOC) per paragraph plus a custom list of occupational nouns
('the official', 'the censor', etc.). Flags 3+ consecutive paragraphs
with zero concrete instances.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import spacy


_NLP = None


def _nlp():
    global _NLP
    if _NLP is None:
        _NLP = spacy.load("en_core_web_sm", disable=["lemmatizer", "tagger"])
    return _NLP


_NER_LABELS = {
    "PERSON", "ORG", "GPE", "DATE", "MONEY", "ORDINAL",
    "EVENT", "NORP", "LOC", "TIME",
}

_OCCUPATIONAL_NOUNS = {
    "official", "censor", "philosopher", "worker", "student", "judge",
    "magistrate", "officer", "professor", "physician", "scholar", "tradesman",
    "soldier", "merchant", "scientist", "clerk", "minister", "barrister",
}


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _concrete_count(para: str) -> int:
    nlp = _nlp()
    doc = nlp(para)
    ner_count = sum(1 for ent in doc.ents if ent.label_ in _NER_LABELS)
    occ_re = re.compile(
        r"\bthe\s+(" + "|".join(re.escape(w) for w in _OCCUPATIONAL_NOUNS) + r")\b",
        flags=re.IGNORECASE,
    )
    occ_count = len(occ_re.findall(para))
    return ner_count + occ_count


def lint_concrete_instance_density(path: Path) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    paras = _paragraphs(text)
    if len(paras) < 3:
        return []
    counts = [_concrete_count(p) for p in paras]

    findings: list[dict] = []
    run_start = None
    flagged = False
    for i, c in enumerate(counts):
        if c == 0:
            if run_start is None:
                run_start = i
            if i - run_start + 1 >= 3 and not flagged:
                # All vitality linters advisory in v1; tier records internal
                # strength for the report, severity stays advisory.
                findings.append({
                    "rule": "concrete-instance-density",
                    "tier": "important",
                    "severity": "advisory",
                    "run_start_paragraph": run_start,
                    "run_length": i - run_start + 1,
                    "message": (
                        f"{i - run_start + 1} consecutive paragraphs with zero concrete "
                        f"instances (PERSON/ORG/GPE/DATE/MONEY/ORDINAL or occupational noun)."
                    ),
                })
                flagged = True
        else:
            run_start = None

    avg = sum(counts) / len(counts)
    if avg < 0.5 and not findings:
        findings.append({
            "rule": "concrete-instance-density",
            "severity": "advisory",
            "avg_per_paragraph": round(avg, 2),
            "message": f"Average concrete-instance density {avg:.2f} below 0.5/paragraph.",
        })

    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_concrete_instance_density(Path(sys.argv[1])), indent=2))
