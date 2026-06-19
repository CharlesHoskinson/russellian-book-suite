"""Live chapter drafting from retrieval bundles."""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import chapter_bundle
from . import writer_assertion
from .sibling_skills import load_book_qa_module


class DraftChapterError(Exception):
    pass


@dataclass(frozen=True)
class DraftChapterResult:
    chapter_id: str
    draft_path: Path
    prompt_path: Path
    scaffold_path: Path
    prompt: str
    scaffold: dict[str, Any]
    assertions: list[dict[str, Any]]
    facts: list[dict[str, Any]]
    publication_results: list[dict[str, Any]]


def _require_llm(llm_call: Callable[[str], str] | None) -> Callable[[str], str]:
    if llm_call is None:
        raise DraftChapterError("draft_chapter requires an injected llm_call")
    return llm_call


def _anchor_by_claim(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    anchors: dict[str, dict[str, Any]] = {}
    for anchor in payload.get("source-span-anchors") or []:
        claim_id = anchor.get("claim-id")
        if claim_id and claim_id not in anchors:
            anchors[claim_id] = anchor
    return anchors


def _unanchored_claim_ids(payload: dict[str, Any]) -> set[str]:
    flags = payload.get("flags") or {}
    return {
        item.get("claim-id")
        for item in flags.get("unanchored-load-bearing") or []
        if item.get("claim-id")
    }


def _code_grounding(payload: dict[str, Any], support_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links_by_claim = payload.get("code-links") or {}
    rows: list[dict[str, Any]] = []
    for claim in support_claims:
        claim_id = claim["claim-id"]
        links = links_by_claim.get(claim_id) or []
        for link in sorted(links, key=lambda item: str(item.get("code-id") or "")):
            code_id = str(link.get("code-id") or "").strip()
            if not code_id:
                continue
            row = {
                "claim-id": claim_id,
                "code-id": code_id,
            }
            for source_key, target_key in (
                ("code-label", "code-label"),
                ("label", "code-label"),
                ("source-file", "source-file"),
                ("source_file", "source-file"),
                ("kind", "link-kind"),
                ("link-kind", "link-kind"),
            ):
                if link.get(source_key):
                    row[target_key] = link[source_key]
            rows.append(row)
    return rows


def build_bundle_scaffold(bundle: dict[str, Any]) -> dict[str, Any]:
    """Build the deterministic writer scaffold consumed by the live draft path."""
    payload = bundle["payload"]
    anchors = _anchor_by_claim(payload)
    flagged_unanchored = _unanchored_claim_ids(payload)
    support_claims: list[dict[str, Any]] = []
    withheld: list[dict[str, str]] = []

    for claim in payload.get("load-bearing-claims") or []:
        claim_id = claim["claim-id"]
        anchor = anchors.get(claim_id)
        if claim_id in flagged_unanchored or anchor is None:
            withheld.append({
                "claim-id": claim_id,
                "reason": "no-source-span" if claim_id in flagged_unanchored else "no-anchor",
            })
            continue
        support_claims.append({
            "claim-id": claim_id,
            "text": claim.get("text", ""),
            "anchor": anchor,
        })

    flags = dict(payload.get("flags") or {})
    if withheld and "unanchored-load-bearing" not in flags:
        flags["unanchored-load-bearing"] = withheld

    scaffold = {
        "schema": "claim-first-drafting-scaffold/v1",
        "chapter-id": payload["chapter-id"],
        "thesis-cue": bundle.get("prompt_scaffold", "").strip(),
        "dominant-communities": payload.get("dominant-communities") or [],
        "support-claims": support_claims,
        "caveats": payload.get("unresolved-rebuttals") or [],
        "flags": flags,
    }
    code_grounding = _code_grounding(payload, support_claims)
    if code_grounding:
        scaffold["code-grounding"] = code_grounding
    return scaffold


def _format_anchor(anchor: dict[str, Any]) -> str:
    parts = [f"span {anchor.get('span-id')}"]
    doc_id = anchor.get("doc-id")
    if doc_id:
        parts.append(f"doc {doc_id}")
    page = anchor.get("page-index")
    if page is not None:
        parts.append(f"page {page}")
    locator = anchor.get("locator-text")
    if locator:
        parts.append(str(locator))
    return "; ".join(parts)


def render_drafting_prompt(scaffold: dict[str, Any]) -> str:
    """Render a bounded claim-first prompt from a bundle scaffold."""
    lines: list[str] = [
        scaffold["thesis-cue"],
        "",
        f"Draft chapter {scaffold['chapter-id']} from the support below.",
        "Use only anchored support claims as assertable claims.",
    ]

    communities = scaffold.get("dominant-communities") or []
    if communities:
        top = communities[0]
        lines.extend([
            "",
            "Thesis context:",
            f"- Dominant community {top.get('community-id')} covers {top.get('claim-count')} load-bearing claims.",
        ])

    support_claims = scaffold.get("support-claims") or []
    if support_claims:
        lines.extend(["", "Support claims:"])
        for idx, item in enumerate(support_claims, start=1):
            anchor = _format_anchor(item["anchor"])
            lines.append(
                f"{idx}. {item['claim-id']} [{anchor}] {item.get('text', '').strip()}"
            )
    else:
        lines.extend(["", "Support claims: (none anchored)"])

    code_grounding = scaffold.get("code-grounding") or []
    if code_grounding:
        lines.extend(["", "Code grounding:"])
        for item in code_grounding:
            code_text = item["code-id"]
            details = [
                str(item[key])
                for key in ("code-label", "source-file", "link-kind")
                if item.get(key)
            ]
            if details:
                code_text += f" ({'; '.join(details)})"
            lines.append(f"- {item['claim-id']} -> {code_text}")

    caveats = scaffold.get("caveats") or []
    if caveats:
        lines.extend(["", "Caveats:"])
        for caveat in caveats:
            lines.append(
                "- "
                f"{caveat.get('counter-claim-id')} targets "
                f"{caveat.get('target-claim-id')}; present the target claim with this caveat."
            )

    unanchored = (scaffold.get("flags") or {}).get("unanchored-load-bearing") or []
    if unanchored:
        rendered = ", ".join(
            f"{item.get('claim-id')} ({item.get('reason')})" for item in unanchored
        )
        lines.extend([
            "",
            f"Flags: Do not assert unanchored load-bearing claims: {rendered}.",
        ])

    lines.extend([
        "",
        "Write concise prose. Do not introduce unanchored factual claims.",
    ])
    return "\n".join(line.rstrip() for line in lines if line is not None).strip() + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _default_faithfulness(_prompt: str) -> str:
    return "full"


def _default_revise(sentence: str, _span_text: str) -> str:
    return sentence


def _default_decomposer(_prompt: str) -> str:
    return "[]"


def _default_proposal_writer(workspace: Path, proposals: list[dict]) -> Path:
    module = load_book_qa_module("attributed_generation_writeback")
    return module.write_novel_draft_claim_proposals(workspace, proposals)


def _split_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]


def _split_sentences(paragraph: str) -> list[str]:
    sentences = [
        match.group(0).strip()
        for match in re.finditer(r"[^.!?]+(?:[.!?]+|$)", paragraph)
        if match.group(0).strip()
    ]
    return sentences or ([paragraph.strip()] if paragraph.strip() else [])


def _claim_binding(scaffold: dict[str, Any], index: int) -> dict[str, Any]:
    claims = scaffold.get("support-claims") or []
    if not claims:
        raise DraftChapterError("cannot bind generated sentence without anchored support claims")
    return claims[min(index, len(claims) - 1)]


def _span_text_by_id(scaffold: dict[str, Any]) -> dict[str, str]:
    spans: dict[str, str] = {}
    for claim in scaffold.get("support-claims") or []:
        anchor = claim["anchor"]
        span_id = anchor.get("span-id")
        if span_id:
            spans[span_id] = str(anchor.get("locator-text") or claim.get("text") or "")
    return spans


def _known_claims(scaffold: dict[str, Any]) -> dict[str, str]:
    return {
        item["claim-id"]: item.get("text", "")
        for item in scaffold.get("support-claims") or []
    }


def draft_chapter(
    workspace: Path,
    chapter_id: str,
    *,
    llm_call: Callable[[str], str] | None = None,
    faithfulness_llm_call: Callable[[str], Any] | None = None,
    revise_call: Callable[[str, str], str] | None = None,
    decomposer_llm_call: Callable[[str], Any] | None = None,
    proposal_writer: Callable[[Path, list[dict]], Path] | None = None,
) -> DraftChapterResult:
    """Draft a chapter from the live chapter-retrieval bundle scaffold."""
    llm = _require_llm(llm_call)
    faithfulness = faithfulness_llm_call or _default_faithfulness
    revise = revise_call or _default_revise
    decompose = decomposer_llm_call or _default_decomposer
    write_proposals = proposal_writer or _default_proposal_writer
    workspace = Path(workspace)
    bundle = chapter_bundle.build_chapter_bundle_input(workspace, chapter_id)
    scaffold = build_bundle_scaffold(bundle)
    prompt = render_drafting_prompt(scaffold)
    generated_text = str(llm(prompt)).strip()

    chapter_dir = workspace / "chapters" / "drafts" / chapter_id
    chapter_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = chapter_dir / "draft-prompt.md"
    scaffold_path = chapter_dir / "draft-scaffold.json"
    draft_path = chapter_dir / "draft.md"
    assertions_path = chapter_dir / "writer-assertions.jsonl"
    blocked_path = chapter_dir / "blocked-paragraphs.json"
    prompt_path.write_text(prompt, encoding="utf-8")
    _write_json(scaffold_path, scaffold)

    span_text = _span_text_by_id(scaffold)
    known_claims = _known_claims(scaffold)
    assertions: list[dict[str, Any]] = []
    all_facts: list[dict[str, Any]] = []
    publication_results: list[dict[str, Any]] = []
    published_paragraphs: list[str] = []
    sentence_index = 0

    for paragraph_index, paragraph in enumerate(_split_paragraphs(generated_text), start=1):
        paragraph_id = f"p{paragraph_index:03d}"
        published_sentences: list[str] = []
        for sentence in _split_sentences(paragraph):
            binding = _claim_binding(scaffold, sentence_index)
            anchor = binding["anchor"]
            assertion = writer_assertion.record_generated_sentence(
                workspace,
                chapter_id=chapter_id,
                paragraph_id=paragraph_id,
                sentence_index=sentence_index + 1,
                sentence_text=sentence,
                asserts_claim=[binding["claim-id"]],
                cites_span=[anchor["span-id"]],
            )
            resolved = writer_assertion.resolve_for_publication(
                assertion,
                span_text,
                llm_call=faithfulness,
                revise_call=revise,
            )
            assertions.append(resolved)
            published_sentences.append(resolved["published_text"])
            sentence_index += 1

        published_paragraph = " ".join(published_sentences).strip()
        facts = writer_assertion.decompose_paragraph(
            published_paragraph,
            known_claims,
            llm_call=decompose,
            chapter_id=chapter_id,
            paragraph_id=paragraph_id,
        )
        writer_assertion.record_atomic_facts(workspace, chapter_id, facts)
        all_facts.extend(facts)
        publication = writer_assertion.evaluate_paragraph_publication(
            workspace,
            chapter_id,
            paragraph_id,
            facts,
            proposal_writer=write_proposals,
        )
        publication_results.append(publication)
        if publication["passes"]:
            published_paragraphs.append(published_paragraph)

    _write_jsonl(assertions_path, assertions)
    _write_json(
        blocked_path,
        {
            "chapter_id": chapter_id,
            "paragraphs": publication_results,
        },
    )
    assembled = "\n\n".join(published_paragraphs)
    draft_path.write_text((assembled + "\n") if assembled else "", encoding="utf-8")

    return DraftChapterResult(
        chapter_id=chapter_id,
        draft_path=draft_path,
        prompt_path=prompt_path,
        scaffold_path=scaffold_path,
        prompt=prompt,
        scaffold=scaffold,
        assertions=assertions,
        facts=all_facts,
        publication_results=publication_results,
    )
