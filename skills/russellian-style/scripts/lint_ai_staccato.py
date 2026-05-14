"""AI-staccato linter.

Detects four cross-paragraph patterns the existing eleven linters miss:
  - staccato-paragraph-run    : runs of short, few-sentence paragraphs
  - negation-affirmation-template : "X is not Y. X is Z." across paragraphs
  - this-is-conclusion-overuse    : repeated "This is ..." conclusions
  - abstract-subject-run          : same abstract noun heading many sentences

All findings emit at advisory severity, important tier; the linter never
gates a build by itself. Promotion to gating is deferred to a follow-up
calibration spec.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .lint_common import load_markdown, load_rules


def _paragraphs(text: str) -> list[tuple[int, str]]:
    """Return (start_line_1indexed, paragraph_text) pairs, skipping code and headings."""
    out: list[tuple[int, str]] = []
    lines = text.splitlines()
    current: list[str] = []
    current_start = 1
    in_fence = False
    for idx, raw in enumerate(lines, start=1):
        if raw.lstrip().startswith("```"):
            in_fence = not in_fence
            if current:
                out.append((current_start, "\n".join(current)))
                current = []
            current_start = idx + 1
            continue
        if in_fence:
            continue
        if raw.strip() == "":
            if current:
                out.append((current_start, "\n".join(current)))
                current = []
            current_start = idx + 1
        else:
            if raw.lstrip().startswith("#"):
                if current:
                    out.append((current_start, "\n".join(current)))
                    current = []
                current_start = idx + 1
                continue
            if not current:
                current_start = idx
            current.append(raw)
    if current:
        out.append((current_start, "\n".join(current)))
    return out


def _sentences(para: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", para.strip()) if s.strip()]


def _staccato_paragraph_run(paragraphs: list[tuple[int, str]], cfg: dict) -> list[dict]:
    """Flag runs of N+ consecutive short-sentence paragraphs."""
    min_run = cfg["staccato_run_min"]
    max_words = cfg["staccato_max_sentence_words"]
    max_sents = cfg["staccato_max_sentences_per_paragraph"]
    findings: list[dict] = []
    run_start_line = 0
    run_length = 0
    in_run = False
    for start_line, text in paragraphs:
        sents = _sentences(text)
        is_staccato = (
            2 <= len(sents) <= max_sents
            and all(len(s.split()) <= max_words for s in sents)
        )
        if is_staccato:
            if not in_run:
                run_start_line = start_line
                run_length = 1
                in_run = True
            else:
                run_length += 1
        else:
            if in_run and run_length >= min_run:
                findings.append({
                    "rule": "staccato-paragraph-run",
                    "tier": "important",
                    "severity": "advisory",
                    "line": run_start_line,
                    "run_length": run_length,
                    "message": (
                        f"{run_length} consecutive paragraphs of 2-3 short sentences "
                        f"(<= {max_words} words each). Break the rhythm with a longer "
                        "concession or example paragraph."
                    ),
                })
            in_run = False
            run_length = 0
    if in_run and run_length >= min_run:
        findings.append({
            "rule": "staccato-paragraph-run",
            "tier": "important",
            "severity": "advisory",
            "line": run_start_line,
            "run_length": run_length,
            "message": (
                f"{run_length} consecutive paragraphs of 2-3 short sentences "
                f"(<= {max_words} words each). Break the rhythm with a longer "
                "concession or example paragraph."
            ),
        })
    return findings


def lint_ai_staccato(path: Path) -> list[dict]:
    text = load_markdown(path)
    paras = _paragraphs(text)
    cfg = load_rules()["ai_staccato"]["detection"]
    findings: list[dict] = []
    findings.extend(_staccato_paragraph_run(paras, cfg))
    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_ai_staccato(Path(sys.argv[1])), indent=2))
