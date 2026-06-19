"""Advisory worked-case scorer: a worked example / contrast / counterexample frame."""
from __future__ import annotations
import re

_CUES = ("for example", "for instance", "think about", "think of", "consider",
         "suppose", "imagine", "picture", "take the case", "say you",
         "unlike", "whereas", "instead of", "rather than", "as if")
_CUE_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in _CUES) + r")\b")


def score(sentences, register, profile) -> dict:
    findings: list[dict] = []
    for i, s in enumerate(sentences):
        m = _CUE_RE.search(s.text.lower())
        if m:
            findings.append({"line": i, "cue": m.group(1)})
    return {"signal": "worked_case", "score": 1.0 if findings else 0.0, "findings": findings}
