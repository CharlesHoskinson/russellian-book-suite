"""Writer assertion records and citation-support policy for generated prose."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from .sibling_skills import load_book_knowledge_module

VALID_STATUSES = {"full", "partial", "none"}
DEFAULT_PROMPT = (
    "Classify whether the cited span supports the sentence.\n"
    "Return exactly one token: full, partial, or none.\n"
    "Sentence: {sentence}\n"
    "Cited spans:\n{spans}\n"
)


class WriterAssertionError(ValueError):
    """Raised when a writer assertion or check result violates the S2 contract."""


def _chapter_dir(workspace: Path, chapter_id: str) -> Path:
    return Path(workspace) / "chapters" / "drafts" / chapter_id


def _assertions_path(workspace: Path, chapter_id: str) -> Path:
    return _chapter_dir(workspace, chapter_id) / "writer-assertions.jsonl"


def _facts_path(workspace: Path, chapter_id: str) -> Path:
    return _chapter_dir(workspace, chapter_id) / "draft-atomic-facts.jsonl"


def _read_jsonl(path: Path) -> list[dict]:
    io_utils = load_book_knowledge_module("io_utils")
    return io_utils.read_jsonl(path)


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def _assertion_id(chapter_id: str, paragraph_id: str, sentence_index: int) -> str:
    return f"wa-{chapter_id}-{paragraph_id}-{sentence_index:04d}"


def _fact_id(chapter_id: str, paragraph_id: str, fact_index: int) -> str:
    return f"fact-{chapter_id}-{paragraph_id}-{fact_index:04d}"


def _novel_id(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"novel-{digest}"


def _require_non_empty(name: str, values: Iterable[str]) -> list[str]:
    out = [str(v) for v in values if str(v)]
    if not out:
        raise WriterAssertionError(f"{name} must contain at least one id")
    return out


def record_writer_assertion(
    workspace: Path,
    *,
    chapter_id: str,
    paragraph_id: str,
    sentence_index: int,
    sentence_text: str,
    asserts_claim: list[str],
    cites_span: list[str],
) -> dict:
    """Append one writer assertion under the chapter draft directory."""
    claims = _require_non_empty("asserts_claim", asserts_claim)
    spans = _require_non_empty("cites_span", cites_span)
    record = {
        "id": _assertion_id(chapter_id, paragraph_id, sentence_index),
        "chapter_id": chapter_id,
        "paragraph_id": paragraph_id,
        "sentence_index": sentence_index,
        "sentence_text": sentence_text,
        "asserts_claim": claims,
        "cites_span": spans,
        "citation_check_status": None,
        "revision_origin": None,
        "published_text": None,
        "flags": [],
    }
    _append_jsonl(_assertions_path(workspace, chapter_id), record)
    return record


def record_generated_sentence(
    workspace: Path,
    *,
    chapter_id: str,
    paragraph_id: str,
    sentence_index: int,
    sentence_text: str,
    asserts_claim: list[str],
    cites_span: list[str],
) -> dict:
    """Record the assertion created at sentence-generation time."""
    return record_writer_assertion(
        workspace,
        chapter_id=chapter_id,
        paragraph_id=paragraph_id,
        sentence_index=sentence_index,
        sentence_text=sentence_text,
        asserts_claim=asserts_claim,
        cites_span=cites_span,
    )


def read_writer_assertions(workspace: Path, chapter_id: str) -> list[dict]:
    return _read_jsonl(_assertions_path(workspace, chapter_id))


def _span_block(assertion: dict, span_text_by_id: dict[str, str]) -> str:
    lines: list[str] = []
    for span_id in assertion.get("cites_span", []):
        lines.append(f"- {span_id}: {span_text_by_id.get(span_id, '')}")
    return "\n".join(lines)


def _parse_status(raw: Any) -> str:
    if isinstance(raw, dict):
        raw = (
            raw.get("citation_check_status")
            or raw.get("status")
            or raw.get("support")
        )
    if not isinstance(raw, str):
        raise WriterAssertionError(f"invalid citation check response: {raw!r}")
    text = raw.strip()
    if text.startswith("{"):
        try:
            return _parse_status(json.loads(text))
        except json.JSONDecodeError as exc:
            raise WriterAssertionError(f"invalid citation check JSON: {text!r}") from exc
    status = text.lower().split()[0].strip(".,:;")
    if status not in VALID_STATUSES:
        raise WriterAssertionError(f"invalid citation check status: {status!r}")
    return status


def check_writer_assertion(
    assertion: dict,
    span_text_by_id: dict[str, str],
    *,
    llm_call: Callable[[str], Any],
    prompt_template: str = DEFAULT_PROMPT,
) -> dict:
    """Run the offline injected support check and return an updated assertion."""
    prompt = prompt_template.format(
        sentence=assertion["sentence_text"],
        spans=_span_block(assertion, span_text_by_id),
    )
    status = _parse_status(llm_call(prompt))
    out = dict(assertion)
    out["citation_check_status"] = status
    return out


def _hedged(sentence: str) -> str:
    return f"The cited material offers partial support for this claim: {sentence}"


def resolve_for_publication(
    assertion: dict,
    span_text_by_id: dict[str, str],
    *,
    llm_call: Callable[[str], Any],
    revise_call: Callable[[str, str], str],
) -> dict:
    """Apply the S2 revise-or-downgrade publication policy."""
    checked = check_writer_assertion(assertion, span_text_by_id, llm_call=llm_call)
    trigger = checked["citation_check_status"]
    original = checked["sentence_text"]
    if trigger == "full":
        out = dict(checked)
        out["published_text"] = original
        out["revision_origin"] = {"trigger_status": "full", "action": "unrevised"}
        return out

    span_text = "\n".join(span_text_by_id.get(sid, "") for sid in checked["cites_span"])
    revised_text = revise_call(original, span_text).strip()
    if revised_text and revised_text != original:
        candidate = dict(checked, sentence_text=revised_text)
        rechecked = check_writer_assertion(candidate, span_text_by_id, llm_call=llm_call)
        if rechecked["citation_check_status"] == "full":
            rechecked["published_text"] = revised_text
            rechecked["revision_origin"] = {
                "trigger_status": trigger,
                "action": "revised-from-span",
            }
            return rechecked

    out = dict(checked)
    out["published_text"] = _hedged(original)
    out["flags"] = sorted(set(out.get("flags", [])) | {"partial-support"})
    out["revision_origin"] = {
        "trigger_status": trigger,
        "action": "downgraded-partial-support",
    }
    return out


def _parse_facts(raw: Any) -> list[dict]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise WriterAssertionError("atomic fact decomposer returned invalid JSON") from exc
    if isinstance(raw, dict):
        raw = raw.get("facts")
    if not isinstance(raw, list):
        raise WriterAssertionError("atomic fact decomposer must return a list")
    facts: list[dict] = []
    for item in raw:
        if isinstance(item, str):
            facts.append({"text": item})
        elif isinstance(item, dict) and item.get("text"):
            facts.append(dict(item))
        else:
            raise WriterAssertionError(f"invalid atomic fact item: {item!r}")
    return facts


def decompose_paragraph(
    paragraph_text: str,
    known_claims: dict[str, str],
    *,
    llm_call: Callable[[str], Any],
    chapter_id: str,
    paragraph_id: str,
) -> list[dict]:
    """Decompose a paragraph and map every fact to a claim or novel draft claim."""
    prompt = (
        "Decompose the paragraph into atomic facts as JSON.\n"
        f"Paragraph: {paragraph_text}\n"
    )
    raw_facts = _parse_facts(llm_call(prompt))
    text_to_claim = {text: claim_id for claim_id, text in known_claims.items()}
    out: list[dict] = []
    for idx, item in enumerate(raw_facts, start=1):
        text = str(item["text"])
        claim_id = item.get("claim_id")
        if claim_id not in known_claims:
            claim_id = text_to_claim.get(text)
        novel = None if claim_id else _novel_id(text)
        out.append(
            {
                "id": _fact_id(chapter_id, paragraph_id, idx),
                "chapter_id": chapter_id,
                "paragraph_id": paragraph_id,
                "text": text,
                "claim_id": claim_id,
                "novel_draft_claim": novel,
            }
        )
    return out


def record_atomic_facts(workspace: Path, chapter_id: str, facts: list[dict]) -> None:
    for fact in facts:
        _append_jsonl(_facts_path(workspace, chapter_id), fact)


def evaluate_paragraph_publication(
    workspace: Path,
    chapter_id: str,
    paragraph_id: str,
    facts: list[dict],
    *,
    proposal_writer: Callable[[Path, list[dict]], Path] | None = None,
) -> dict:
    """Block paragraphs with novel draft claims and return QA proposal records."""
    novel = [f for f in facts if f.get("novel_draft_claim")]
    proposals = [
        {
            "kind": "novel_draft_claim",
            "novel_draft_claim": fact["novel_draft_claim"],
            "text": fact["text"],
            "chapter_id": chapter_id,
            "paragraph_id": paragraph_id,
            "fact_id": fact["id"],
            "requires": "human-review",
            "auto_apply": False,
        }
        for fact in novel
    ]
    proposal_path = None
    if proposals and proposal_writer is not None:
        proposal_path = proposal_writer(Path(workspace), proposals)
    return {
        "passes": not novel,
        "blocked_by": [f["novel_draft_claim"] for f in novel],
        "proposals": proposals,
        "proposal_path": str(proposal_path) if proposal_path is not None else None,
    }
