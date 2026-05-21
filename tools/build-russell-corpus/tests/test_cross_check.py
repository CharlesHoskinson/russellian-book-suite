import json
from pathlib import Path

from scripts.cross_check import run_cross_check, CrossCheckOutcome


FIXTURES = Path(__file__).parent / "fixtures"
CANDIDATES = FIXTURES / "candidates"
VOCABULARY = Path(__file__).parent.parent / "assets" / "vocabulary.json"


def _llm_agrees_with_tag(prompt: str) -> str:
    return json.dumps({
        "top1_tag": "domain_contrast",
        "top3_tags": ["domain_contrast", "antithesis", "diagnosis"],
        "is_quotation": False,
        "lesson_specific_to_paragraph": True,
        "lesson_specificity_evidence": "names the exact two domains Russell splits"
    })


def _llm_disagrees_with_tag(prompt: str) -> str:
    return json.dumps({
        "top1_tag": "diagnosis",
        "top3_tags": ["diagnosis", "concession", "definition"],
        "is_quotation": False,
        "lesson_specific_to_paragraph": True,
        "lesson_specificity_evidence": "diagnoses an error before correcting"
    })


def _llm_flags_quotation(prompt: str) -> str:
    return json.dumps({
        "top1_tag": "concession",
        "top3_tags": ["concession", "diagnosis", "antithesis"],
        "is_quotation": True,
        "lesson_specific_to_paragraph": True,
        "lesson_specificity_evidence": "the words are Hume's, not Russell's"
    })


def _llm_flags_generic_lesson(prompt: str) -> str:
    return json.dumps({
        "top1_tag": "domain_contrast",
        "top3_tags": ["domain_contrast", "antithesis", "diagnosis"],
        "is_quotation": False,
        "lesson_specific_to_paragraph": False,
        "lesson_specificity_evidence": "the lesson could apply to most of Russell"
    })


def test_cross_check_passes_when_extractor_tag_in_top3() -> None:
    candidate = json.loads((CANDIDATES / "good.json").read_text())
    outcome = run_cross_check(candidate=candidate, vocabulary_path=VOCABULARY, llm_call=_llm_agrees_with_tag)
    assert outcome.status == "pass"


def test_cross_check_rejects_tag_disagreement() -> None:
    candidate = json.loads((CANDIDATES / "wrong_tag.json").read_text())
    outcome = run_cross_check(candidate=candidate, vocabulary_path=VOCABULARY, llm_call=_llm_disagrees_with_tag)
    assert outcome.status == "reject"
    assert outcome.reason == "tag-disagreement"
    assert outcome.evidence["extractor_tag"] == "antithesis"
    assert outcome.evidence["cross_check_top3"] == ["diagnosis", "concession", "definition"]


def test_cross_check_rejects_quotation() -> None:
    candidate = json.loads((CANDIDATES / "quoting_hume.json").read_text())
    outcome = run_cross_check(candidate=candidate, vocabulary_path=VOCABULARY, llm_call=_llm_flags_quotation)
    assert outcome.status == "reject"
    assert outcome.reason == "russell-quoting-other-author"


def test_cross_check_rejects_generic_lesson() -> None:
    candidate = json.loads((CANDIDATES / "good.json").read_text())
    outcome = run_cross_check(candidate=candidate, vocabulary_path=VOCABULARY, llm_call=_llm_flags_generic_lesson)
    assert outcome.status == "reject"
    assert outcome.reason == "lesson-generic-cross-check"
