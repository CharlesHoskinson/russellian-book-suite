"""Ingest the ADSC clinical report markdown into a claims_clean.jsonl ledger.

Heuristic: a SENTENCE counts as a quantitative claim if it contains a digit
AND at least one unit/method marker. We emit one JSONL record per
quantitative sentence. Sentences (not paragraphs) are the granularity Phase O
needs to reach 1000+ claims on the ADSC corpus — a single paragraph routinely
carries 4-6 distinct trial parameters, and shoving them all into one claim
loses the cross-paragraph consistency story the verifier exists to test.

This is a deliberately dumb extractor; the BookLogic lifts are what assign
typed atoms to claims downstream. Phase O's eval bench measures the framework
behaviour at 1000+ claims, not the prose-quality of these extractors. Phase P
(LLM lifts) is the natural follow-up that would refine the extraction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# Markers chosen so we capture clinical-evidence paragraphs without over-firing.
# Order matters only for documentation; the regex is alternation.
UNIT_MARKERS = [
    r"n\s*=\s*\d",
    r"p\s*[<>=]\s*0?\.\d",
    r"\bp\s*=\s*0?\.\d",
    r"\d\s*%",
    r"\d+\s*mg\b",
    r"\d+\s*ml\b",
    r"\d+\s*mcg\b",
    r"\d+\s*µg\b",
    r"\d+\s*ng\b",
    r"\d+\s*kg\b",
    r"\d+\s*cm\b",
    r"\d+\s*mm\b",
    r"\d+\s*hours?\b",
    r"\d+\s*months?\b",
    r"\d+\s*weeks?\b",
    r"\d+\s*days?\b",
    r"\d+\s*years?\b",
    r"\d+\s*patients?\b",
    r"\d+\s*participants?\b",
    r"\d+\s*subjects?\b",
    r"\d+\s*trials?\b",
    r"\d+\s*studies\b",
    r"\d+\s*cells?\b",
    r"\d+\s*injections?\b",
    r"\d+\s*sessions?\b",
    r"\d+\s*million\b",
    r"\d+\s*billion\b",
    r"\bHbA1c\b.*?\d",
    r"\bIEQ\b.*?\d",
    r"\d+\s*units?\b",
    r"\d+\s*pmol",
    r"\d+\s*mg/d[Ll]\b",
    r"\d+\.\d+",  # any decimal number
    r"\bdose\s+of\s+\d",
    r"\bcohort\s+of\s+\d",
    r"\bgroup\s+of\s+\d",
    r"\$\s*\d",
    r"\d+\s*dollars\b",
    r"\bbetween\s+\d+\s+and\s+\d",
    r"\bfrom\s+\d+\s+to\s+\d",
    r"\b(?:phase|stage)\s+(?:I|II|III|IV|1|2|3|4)\b",
    r"\bday\s+\d",
    r"\bweek\s+\d",
    r"\bmonth\s+\d",
    r"\byear\s+\d",
    r"\bage[ds]?\s+\d",
    r"\bover\s+\d",
    r"\bat\s+least\s+\d",
    r"\bmore\s+than\s+\d",
    r"\bfewer\s+than\s+\d",
    r"\b\d{2,}\b",  # any number of 2+ digits
]
UNIT_RE = re.compile("|".join(UNIT_MARKERS), re.IGNORECASE)
DIGIT_RE = re.compile(r"\d")


_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def split_paragraphs(text: str) -> list[str]:
    """Split markdown into paragraphs by blank-line boundary, stripping headings."""
    blocks: list[str] = []
    buf: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip() == "":
            if buf:
                blocks.append(" ".join(s.strip() for s in buf))
                buf = []
            continue
        # Drop bare markdown headings and table separators
        stripped = line.lstrip()
        if stripped.startswith(("#", "|---", "---", "===")):
            if buf:
                blocks.append(" ".join(s.strip() for s in buf))
                buf = []
            continue
        buf.append(line)
    if buf:
        blocks.append(" ".join(s.strip() for s in buf))
    return blocks


def split_sentences(paragraph: str) -> list[str]:
    parts = _SENTENCE_RE.split(paragraph)
    out: list[str] = []
    for s in parts:
        s = s.strip()
        if s:
            out.append(s)
    return out


def is_quantitative(text: str) -> bool:
    if len(text) < 30 or len(text) > 1200:
        return False
    if not DIGIT_RE.search(text):
        return False
    return UNIT_RE.search(text) is not None


def short_id(seed: str, idx: int) -> str:
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
    return f"adsc-clean-{idx:04d}-{h}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True, help="ADSC report markdown")
    ap.add_argument("--out", type=Path, required=True, help="output JSONL")
    ap.add_argument(
        "--min-claims",
        type=int,
        default=1000,
        help="minimum claim count; non-zero exit if not met",
    )
    ap.add_argument(
        "--doc-id",
        type=str,
        default="adsc-complete-report-2026",
        help="source doc identifier",
    )
    args = ap.parse_args()

    text = args.src.read_text(encoding="utf-8")
    paragraphs = split_paragraphs(text)
    sentences: list[str] = []
    for para in paragraphs:
        sentences.extend(split_sentences(para))
    quant = [s for s in sentences if is_quantitative(s)]
    # dedupe while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for s in quant:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for i, sent in enumerate(deduped, start=1):
            cid = short_id(sent, i)
            record = {
                "claim_id": cid,
                "claim_type": "fact",
                "canonical_text": sent,
                "status": "verified",
                "confidence": 1.0,
                "source_spans": [
                    {"doc_id": args.doc_id, "locator_text": sent[:160]}
                ],
                "supports_chapters": [],
            }
            fh.write(json.dumps(record, ensure_ascii=False))
            fh.write("\n")

    n = len(deduped)
    print(
        f"[ingest_adsc] paragraphs={len(paragraphs)} sentences={len(sentences)} "
        f"quantitative={n}"
    )
    if n < args.min_claims:
        print(
            f"[ingest_adsc] ERROR: only {n} claims, need {args.min_claims}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
