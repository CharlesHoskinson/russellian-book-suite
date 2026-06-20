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

from .lint_common import _is_code_block, _is_heading, _is_list_marker, _split_paragraphs


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
    # Reuse lint_common's splitter and skip structural markdown (headings,
    # fenced/indented code, list markers) so they do not count as
    # zero-concrete-instance paragraphs and inflate the consecutive-zero run.
    out: list[str] = []
    for _start_line, para in _split_paragraphs(text):
        if _is_code_block(para) or _is_heading(para) or _is_list_marker(para):
            continue
        stripped = para.strip()
        if stripped:
            out.append(stripped)
    return out


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
    run_start: int | None = None

    def _flush(start: int, end_exclusive: int) -> None:
        run_length = end_exclusive - start
        if run_length < 3:
            return
        # All vitality linters advisory in v1; tier records internal
        # strength for the report, severity stays advisory.
        findings.append({
            "rule": "concrete-instance-density",
            "tier": "important",
            "severity": "advisory",
            "run_start_paragraph": start,
            "run_length": run_length,
            "message": (
                f"{run_length} consecutive paragraphs with zero concrete "
                f"instances (PERSON/ORG/GPE/DATE/MONEY/ORDINAL or occupational noun)."
            ),
        })

    # Emit one finding per distinct zero-instance run, not just the first.
    for i, c in enumerate(counts):
        if c == 0:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None:
                _flush(run_start, i)
                run_start = None
    if run_start is not None:
        _flush(run_start, len(counts))

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
