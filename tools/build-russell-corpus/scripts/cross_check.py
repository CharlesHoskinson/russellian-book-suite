"""Cross-check — independent LLM tag verifier and lesson specificity check.

Receives only the paragraph text and the controlled vocabulary; does NOT see the
extractor's proposed tag or calibration lesson. The check rules:

  - extractor's tag must appear in the cross-check's top-3 tags
  - is_quotation must be false
  - lesson_specific_to_paragraph must be true

Any failure rejects the candidate with the matching reason code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from scripts.corpus_io import append_jsonl


_CROSS_CHECK_PROMPT = """You are reviewing one paragraph from a Bertrand Russell text.

Classify the paragraph's rhetorical move using only tags from the controlled vocabulary
provided below. Return JSON with these fields:

  top1_tag: <best tag>
  top3_tags: [<best>, <second>, <third>]
  is_quotation: <true if Russell is quoting another author, else false>
  lesson_specific_to_paragraph: <true if the given lesson is specific to THIS paragraph,
                                 false if it could apply to most of Russell>
  lesson_specificity_evidence: <one-line justification>

PARAGRAPH:
{{PARAGRAPH}}

CANDIDATE'S CALIBRATION LESSON (judge specificity only; do not let it bias your tagging):
{{LESSON}}

CONTROLLED VOCABULARY:
{{VOCABULARY}}
"""


@dataclass
class CrossCheckOutcome:
    status: str  # "pass" | "reject"
    reason: str | None
    evidence: dict[str, Any] | None


def run_cross_check(
    *,
    candidate: dict[str, Any],
    vocabulary_path: Path,
    llm_call: Callable[[str], str],
) -> CrossCheckOutcome:
    vocabulary = vocabulary_path.read_text(encoding="utf-8")
    prompt = (
        _CROSS_CHECK_PROMPT
        .replace("{{PARAGRAPH}}", candidate["paragraph_text"])
        .replace("{{LESSON}}", candidate["calibration_lesson"])
        .replace("{{VOCABULARY}}", vocabulary)
    )
    response = json.loads(llm_call(prompt))

    if response.get("is_quotation"):
        return CrossCheckOutcome("reject", "russell-quoting-other-author", {"evidence": response.get("lesson_specificity_evidence")})

    extractor_tag = candidate["rhetorical_move_tag"]
    if extractor_tag not in response["top3_tags"]:
        return CrossCheckOutcome(
            "reject",
            "tag-disagreement",
            {"extractor_tag": extractor_tag, "cross_check_top3": response["top3_tags"]},
        )

    if not response.get("lesson_specific_to_paragraph"):
        return CrossCheckOutcome("reject", "lesson-generic-cross-check", {"evidence": response.get("lesson_specificity_evidence")})

    return CrossCheckOutcome("pass", None, None)


def run_cross_check_batch(
    *,
    passed_sentinel_path: Path,
    rejected_path: Path,
    verified_path: Path,
    vocabulary_path: Path,
    llm_call: Callable[[str], str],
) -> None:
    """Iterate passed-sentinel.jsonl, route each cross-check outcome to verified/rejected."""
    with passed_sentinel_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cand = json.loads(line)
            outcome = run_cross_check(candidate=cand, vocabulary_path=vocabulary_path, llm_call=llm_call)
            if outcome.status == "pass":
                append_jsonl(verified_path, cand)
            else:
                append_jsonl(rejected_path, {
                    "candidate_id": cand["candidate_id"],
                    "reason": outcome.reason,
                    "evidence": outcome.evidence,
                })
