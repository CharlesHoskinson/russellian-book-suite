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
from functools import lru_cache
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


_NEG_AFFIRM_RE = re.compile(
    r"\b(\w[\w\s''-]{0,40}?)\s+(?:is|are|was|were)\s+not\s+[^.!?]+?[.!?]\s+"
    r"(?:\1|It|It is|These|They|Those|This)\s+(?:is|are|was|were)\s+",
    re.IGNORECASE,
)


def _negation_affirmation_template(paragraphs: list[tuple[int, str]], cfg: dict) -> list[dict]:
    """Flag the 'X is not Y. X is Z.' (or variants) template across paragraphs."""
    min_paras = cfg["negation_affirmation_min_paragraphs"]
    hits: list[int] = []
    for start_line, text in paragraphs:
        if _NEG_AFFIRM_RE.search(text):
            hits.append(start_line)
    if len(hits) < min_paras:
        return []
    return [{
        "rule": "negation-affirmation-template",
        "tier": "important",
        "severity": "advisory",
        "line": hits[0],
        "match_count": len(hits),
        "match_lines": hits,
        "message": (
            f"'X is not Y. X is Z.' template matches across {len(hits)} paragraphs. "
            "Vary the rhetorical shape — try a concession, a distinction, or a "
            "consequence-carrying turn."
        ),
    }]


_THIS_IS_RE = re.compile(r"^\s*(?:This|It|These|Those)\s+(?:is|are|was|were)\b", re.IGNORECASE)


def _this_is_conclusion_overuse(paragraphs: list[tuple[int, str]], cfg: dict) -> list[dict]:
    """Flag windows where many paragraphs end on a 'This is …' / 'It is …' sentence."""
    window = cfg["this_is_window"]
    min_hits = cfg["this_is_min"]
    matches: list[int] = []
    for start_line, text in paragraphs:
        sents = _sentences(text)
        if not sents:
            continue
        last = sents[-1]
        if _THIS_IS_RE.match(last):
            matches.append(start_line)
    if not matches:
        return []
    findings: list[dict] = []
    for i in range(len(matches)):
        run = [m for m in matches[i:]
               if _paragraph_distance(matches[i], m, paragraphs) < window]
        if len(run) >= min_hits:
            findings.append({
                "rule": "this-is-conclusion-overuse",
                "tier": "important",
                "severity": "advisory",
                "line": run[0],
                "match_count": len(run),
                "match_lines": run,
                "message": (
                    f"{len(run)} paragraphs in a {window}-paragraph window end "
                    "on a 'This is …' / 'It is …' conclusion. Replace with a "
                    "consequence-carrying sentence."
                ),
            })
            break
    return findings


def _paragraph_distance(line_a: int, line_b: int, paragraphs: list[tuple[int, str]]) -> int:
    """Number of paragraphs between two paragraphs identified by their start lines."""
    idx_a = next((i for i, (l, _) in enumerate(paragraphs) if l == line_a), -1)
    idx_b = next((i for i, (l, _) in enumerate(paragraphs) if l == line_b), -1)
    if idx_a < 0 or idx_b < 0:
        return 99999
    return abs(idx_b - idx_a)


@lru_cache(maxsize=1)
def _nlp_parser():
    import spacy
    return spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])


def _subject_lemma(sentence_doc) -> str | None:
    for token in sentence_doc:
        if token.dep_ == "nsubj":
            return token.lower_
    return None


def _abstract_subject_run(paragraphs: list[tuple[int, str]], cfg: dict) -> list[dict]:
    """Flag runs of N+ consecutive sentences whose nsubj is the same stoplist noun.

    Runs are tracked over the flattened sentence stream so a run that spans a
    paragraph break is detected (the docstring semantics are about consecutive
    sentences, not per-paragraph state). Each finding reports the line of the
    sentence where the run actually started, not the enclosing paragraph's
    first line.
    """
    stoplist = {w.lower() for w in cfg["abstract_subject_stoplist"]}
    min_run = cfg["abstract_subject_min_run"]
    nlp = _nlp_parser()

    # Flatten every sentence across paragraphs, resolving the 1-indexed source
    # line where each sentence begins.
    flat: list[tuple[str | None, int]] = []
    for start_line, text in paragraphs:
        doc = nlp(text)
        for sent in doc.sents:
            line = start_line + text[: sent.start_char].count("\n")
            flat.append((_subject_lemma(sent), line))

    findings: list[dict] = []
    run_subj: str | None = None
    run_len = 0
    run_line = 0
    for subj, line in flat:
        if subj is not None and subj in stoplist and subj == run_subj:
            run_len += 1
        else:
            if run_subj is not None and run_len >= min_run:
                findings.append(_abstract_run_finding(run_subj, run_len, run_line))
            if subj is not None and subj in stoplist:
                run_subj = subj
                run_len = 1
                run_line = line
            else:
                run_subj = None
                run_len = 0
                run_line = 0
    if run_subj is not None and run_len >= min_run:
        findings.append(_abstract_run_finding(run_subj, run_len, run_line))
    return findings


def _abstract_run_finding(subject: str, run_length: int, para_start_line: int) -> dict:
    return {
        "rule": "abstract-subject-run",
        "tier": "important",
        "severity": "advisory",
        "line": para_start_line,
        "subject": subject,
        "run_length": run_length,
        "message": (
            f"{run_length} consecutive sentences share the same abstract subject "
            f"'{subject}'. Vary the agent — particular subjects (an author, a censor, "
            "the worker, the philosopher) keep prose alive."
        ),
    }


def lint_ai_staccato(path: Path) -> list[dict]:
    text = load_markdown(path)
    paras = _paragraphs(text)
    cfg = load_rules()["ai_staccato"]["detection"]
    findings: list[dict] = []
    findings.extend(_staccato_paragraph_run(paras, cfg))
    findings.extend(_negation_affirmation_template(paras, cfg))
    findings.extend(_this_is_conclusion_overuse(paras, cfg))
    findings.extend(_abstract_subject_run(paras, cfg))
    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_ai_staccato(Path(sys.argv[1])), indent=2))
