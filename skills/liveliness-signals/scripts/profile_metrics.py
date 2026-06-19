"""Deterministic, stats-only metrics over corpus text. spaCy for sentence split."""
from __future__ import annotations
from functools import lru_cache
from statistics import mean, pstdev
import spacy


@lru_cache(maxsize=1)
def _nlp():
    nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
    if "sentencizer" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    return nlp


def sentence_lengths(texts: list[str]) -> list[int]:
    nlp = _nlp()
    out: list[int] = []
    for text in texts:
        for sent in nlp(text).sents:
            n = sum(1 for t in sent if not t.is_space and not t.is_punct)
            if n > 0:
                out.append(n)
    return out


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = min(len(sorted_vals) - 1, int(round(p * (len(sorted_vals) - 1))))
    return round(float(sorted_vals[k]), 6)


def cadence_corridor(lengths: list[int]) -> dict:
    if not lengths:
        return {"p10": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0, "cv": 0.0, "count": 0}
    s = sorted(lengths)
    mu = mean(s)
    cv = round(pstdev(s) / mu, 6) if mu else 0.0
    return {
        "p10": _percentile(s, 0.10), "p25": _percentile(s, 0.25),
        "p50": _percentile(s, 0.50), "p75": _percentile(s, 0.75),
        "p90": _percentile(s, 0.90), "cv": cv, "count": len(s),
    }
