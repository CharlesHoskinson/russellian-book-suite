"""Paragraph-motion linter.

Tags each paragraph with one shape using lexical cues, then flags sections
where >70% of paragraphs are flat (assertion_only or assertion_justification).
"""
from __future__ import annotations

import json
import re
from pathlib import Path


SHAPES = (
    "assertion_only",
    "assertion_justification",
    "concession_turn",
    "contrast",
    "example_inference",
    "question_answer",
    "definition_by_pressure",
)


_CONCESSION_MARKERS = re.compile(
    r"\b(but|yet|however|nevertheless|still|even so)\b",
    re.IGNORECASE,
)
_DEFENDER_MARKERS = re.compile(
    r"\b(will say|might claim|argues that|insists that|the defender|the critic)\b",
    re.IGNORECASE,
)
_EXAMPLE_MARKERS = re.compile(
    r"\b(for example|for instance|consider|imagine|take the case)\b",
    re.IGNORECASE,
)
_DEFINITION_MARKERS = re.compile(
    r"\b(as commonly used|as usually understood|in ordinary language|what people mean by)\b",
    re.IGNORECASE,
)
_THEREFORE_MARKERS = re.compile(r"\b(therefore|hence|so that|thus)\b", re.IGNORECASE)


def _sentences(para: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", para.strip()) if s.strip()]


def classify_paragraph(para: str) -> str:
    sents = _sentences(para)
    if not sents:
        return "assertion_only"

    starts_with_question = "?" in sents[0] and sents[0].rstrip().endswith("?")
    if starts_with_question and len(sents) >= 2:
        return "question_answer"

    if _DEFENDER_MARKERS.search(para) and _CONCESSION_MARKERS.search(para):
        return "concession_turn"

    if _EXAMPLE_MARKERS.search(para) and _THEREFORE_MARKERS.search(para):
        return "example_inference"

    if _DEFINITION_MARKERS.search(para):
        return "definition_by_pressure"

    if _CONCESSION_MARKERS.search(para):
        return "contrast"

    if len(sents) <= 1:
        return "assertion_only"

    return "assertion_justification"


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def lint_paragraph_motion(path: Path) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    paras = _paragraphs(text)
    if len(paras) < 3:
        return []
    shapes = [classify_paragraph(p) for p in paras]
    flat = {"assertion_only", "assertion_justification"}
    flat_count = sum(1 for s in shapes if s in flat)
    flat_prop = flat_count / len(shapes)

    findings: list[dict] = []
    if flat_prop > 0.70:
        findings.append({
            "rule": "paragraph-motion",
            "severity": "important",
            "flat_proportion": round(flat_prop, 3),
            "shape_distribution": {
                s: shapes.count(s) for s in SHAPES if shapes.count(s) > 0
            },
            "message": (
                f"{flat_count}/{len(shapes)} paragraphs are flat "
                "(assertion_only or assertion_justification). Add concession, "
                "contrast, definition-by-pressure, or question-answer motion."
            ),
        })
    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_paragraph_motion(Path(sys.argv[1])), indent=2))
