"""Live chapter drafting from retrieval bundles."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import chapter_bundle


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

    return {
        "schema": "claim-first-drafting-scaffold/v1",
        "chapter-id": payload["chapter-id"],
        "thesis-cue": bundle.get("prompt_scaffold", "").strip(),
        "dominant-communities": payload.get("dominant-communities") or [],
        "support-claims": support_claims,
        "caveats": payload.get("unresolved-rebuttals") or [],
        "flags": flags,
    }


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


def draft_chapter(
    workspace: Path,
    chapter_id: str,
    *,
    llm_call: Callable[[str], str] | None = None,
) -> DraftChapterResult:
    """Draft a chapter from the live chapter-retrieval bundle scaffold."""
    llm = _require_llm(llm_call)
    workspace = Path(workspace)
    bundle = chapter_bundle.build_chapter_bundle_input(workspace, chapter_id)
    scaffold = build_bundle_scaffold(bundle)
    prompt = render_drafting_prompt(scaffold)
    draft_text = str(llm(prompt)).rstrip() + "\n"

    chapter_dir = workspace / "chapters" / "drafts" / chapter_id
    chapter_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = chapter_dir / "draft-prompt.md"
    scaffold_path = chapter_dir / "draft-scaffold.json"
    draft_path = chapter_dir / "draft.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    _write_json(scaffold_path, scaffold)
    draft_path.write_text(draft_text, encoding="utf-8")

    return DraftChapterResult(
        chapter_id=chapter_id,
        draft_path=draft_path,
        prompt_path=prompt_path,
        scaffold_path=scaffold_path,
        prompt=prompt,
        scaffold=scaffold,
    )
