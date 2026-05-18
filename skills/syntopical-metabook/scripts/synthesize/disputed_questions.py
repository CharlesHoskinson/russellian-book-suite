"""Generate disputed-question tables by invoking booklogic.disputed_questions
on the verified-claim set. Each topic gets its own markdown file."""
from __future__ import annotations
import os
from pathlib import Path
from collections import defaultdict
from sibling_skills import load_skill_api
from scripts.booklogic_adapter import disputed_questions as _booklogic_disputed_questions
from scripts.provenance import provenance_footer

_LEGACY_BANNER = "> Legacy mode — booklogic disabled"


def _load_book_knowledge():
    return load_skill_api("book-knowledge", expected_major=0)


def _legacy_build_disputed_questions(bk, workspace_root: Path) -> list[Path]:
    """Fallback path: use book-knowledge.detect_conflicts if available."""
    bk.query_claims({"state": "verified"}, workspace_root)
    pairs = []
    try:
        pairs = bk.detect_conflicts(workspace_root)
    except AttributeError:
        pairs = []
    out_dir = workspace_root / "syntopical" / "disputed-questions"
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.md"):
        f.unlink()
    if not pairs:
        return []
    # Group pairs by topic (first tag shared between conflicting claims)
    grouped: dict[str, list] = defaultdict(list)
    for pair in pairs:
        topic = getattr(pair, "topic", "unknown")
        grouped[topic].append(pair)
    written: list[Path] = []
    for topic in sorted(grouped.keys()):
        lines = [_LEGACY_BANNER, "", f"# Disputed Questions: {topic}", "",
                 "| Question | Position | Source | Claim-ID | Rewrite-witness | Evidence locator |",
                 "|---|---|---|---|---|---|"]
        for pair in grouped[topic]:
            question = getattr(pair, "question", "conflict")
            cl_id = getattr(pair, "claim_id", "")
            src_id = getattr(pair, "source_id", "")
            lines.append(f"| {question} | — | {src_id} | {cl_id} | legacy | — |")
        out = out_dir / f"{topic}.md"
        out.write_text("\n".join(lines) + "\n" + provenance_footer(), encoding="utf-8")
        written.append(out)
    return written


def build_disputed_questions(workspace_root: Path) -> list[Path]:
    bk = _load_book_knowledge()
    if os.environ.get("SYNTOPICAL_NO_BOOKLOGIC") == "1":
        return _legacy_build_disputed_questions(bk, workspace_root)
    verified = bk.query_claims({"state": "verified"}, workspace_root)
    results = _booklogic_disputed_questions(verified)
    out_dir = workspace_root / "syntopical" / "disputed-questions"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Clear existing topic files to keep state consistent with current ledger
    for f in out_dir.glob("*.md"):
        f.unlink()
    grouped: dict[str, list] = defaultdict(list)
    for dq in results:
        grouped[dq.topic].append(dq)
    written: list[Path] = []
    for topic in sorted(grouped.keys()):
        dqs = grouped[topic]
        lines = [f"# Disputed Questions: {topic}", ""]
        lines += ["| Question | Position | Source | Claim-ID | Rewrite-witness | Evidence locator |",
                  "|---|---|---|---|---|---|"]
        for dq in dqs:
            for p in dq.positions:
                lines.append(f"| {dq.question} | {p.stance} | {p.source_id} | "
                              f"[{p.claim_id}](../../claims/{p.claim_id}.json) | "
                              f"{p.rewrite_witness} | — |")
        out = out_dir / f"{topic}.md"
        out.write_text("\n".join(lines) + "\n" + provenance_footer(), encoding="utf-8")
        written.append(out)
    return written
