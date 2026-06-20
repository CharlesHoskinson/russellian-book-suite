"""Math/science prose gating for proof obligations."""
from __future__ import annotations

import json
from pathlib import Path


def render_math_science_claim(claim: dict, obligation: dict | None) -> dict:
    """Render a claim only when its proof obligation permits the assertion."""
    text = claim.get("canonical_text", "")
    status = (obligation or {}).get("status")

    if status == "discharged" or obligation is None:
        return {
            "claim_id": claim.get("claim_id"),
            "asserted_verified": True,
            "mode": "verified",
            "sentence": text,
        }

    if status == "waived":
        reason = obligation.get("waiver_reason", "waiver recorded")
        return {
            "claim_id": claim.get("claim_id"),
            "asserted_verified": False,
            "mode": "conjectural",
            "sentence": f"Conjectural: {text} (proof obligation waived: {reason}).",
        }

    return {
        "claim_id": claim.get("claim_id"),
        "asserted_verified": False,
        "mode": "omitted",
        "sentence": "",
    }


def gated_sentence_row(*, chapter: str, rendered: dict, obligation: dict) -> dict:
    """Return the row consumed by the book-qa gated-sentence escape gate."""
    row = {
        "claim_id": rendered.get("claim_id"),
        "obligation_id": obligation.get("id", ""),
        "obligation_status": obligation.get("status", "unknown"),
        "assertion_kind": rendered.get("mode", "omitted"),
        "chapter": chapter,
        "sentence": rendered.get("sentence", ""),
    }
    if obligation.get("status") == "waived" and obligation.get("waiver_reason"):
        row["waiver_reason"] = obligation["waiver_reason"]
    return row


def _append_line(path: Path, text: str) -> None:
    prefix = ""
    if path.exists() and path.read_text(encoding="utf-8").strip():
        prefix = "\n"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{prefix}{text}\n")


def _append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def render_live_math_science_claim(
    workspace: Path | str,
    *,
    chapter: str,
    claim: dict,
    obligation: dict,
) -> dict:
    """Render one live claim and emit the gated-sentence producer row.

    The live pass owns only the rendered chapter text and QA side product. It
    consumes already-authored proof obligations and does not run a verifier.
    """
    workspace = Path(workspace)
    qa_dir = workspace / "qa"
    chapters_dir = workspace / "chapters"
    qa_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)

    rendered = render_math_science_claim(claim, obligation)
    chapter_path = chapters_dir / f"{chapter}.md"
    if rendered.get("sentence"):
        _append_line(chapter_path, rendered["sentence"])

    row = gated_sentence_row(chapter=chapter, rendered=rendered, obligation=obligation)
    gated_path = qa_dir / "gated-sentences.jsonl"
    _append_jsonl(gated_path, row)
    return {
        "rendered": rendered,
        "gated_row": row,
        "chapter_path": chapter_path.as_posix(),
        "gated_sentences_path": gated_path.as_posix(),
    }
