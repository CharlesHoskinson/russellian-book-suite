"""Orchestrator for multi-persona chapter review.

The orchestrator does NOT directly invoke a subagent. It prepares fully-rendered
dispatch packets (prompt + I/O paths) that the calling Claude consumes by issuing
one Task-tool call per packet. After all subagent reports are written,
run_review_pass calls aggregate_reviews to produce persona-review.md.

For testability, run_review_pass accepts an injectable dispatcher callable.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from .aggregate_reviews import aggregate_reviews, AggregatedReview
from .dispatch_review import render_prompt
from .persona_loader import load_all, load_persona


@dataclass(frozen=True)
class DispatchPacket:
    persona_id: str
    persona_display_name: str
    chapter_id: str
    draft_path: Path
    output_path: Path
    prompt: str


def _load_chapter_meta(workspace: Path, chapter_id: str) -> dict:
    contract_path = Path(workspace) / "chapters" / "contracts" / f"{chapter_id}.yaml"
    if contract_path.is_file():
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        return {
            "chapter_id": chapter_id,
            "chapter_title": contract.get("title", ""),
            "chapter_purpose": contract.get("purpose", ""),
            "audience": contract.get("audience", ""),
        }
    return {"chapter_id": chapter_id, "chapter_title": "", "chapter_purpose": "", "audience": ""}


def prepare_dispatch_packets(workspace: Path, chapter_id: str,
                              personas: list[str] | None = None) -> list[DispatchPacket]:
    workspace = Path(workspace).resolve()
    draft_path = workspace / "chapters" / "drafts" / chapter_id / "draft.md"
    if not draft_path.is_file():
        raise FileNotFoundError(f"draft not found: {draft_path}")

    chapter_meta = _load_chapter_meta(workspace, chapter_id)

    if personas is None:
        persona_records = load_all()
    else:
        persona_records = [load_persona(p) for p in personas]

    reviews_dir = workspace / "chapters" / "drafts" / chapter_id / "reviews"
    packets: list[DispatchPacket] = []
    for persona in persona_records:
        out = reviews_dir / f"{persona.persona_id}.md"
        prompt = render_prompt(persona, draft_path, chapter_meta, out)
        packets.append(DispatchPacket(
            persona_id=persona.persona_id,
            persona_display_name=persona.display_name,
            chapter_id=chapter_id,
            draft_path=draft_path,
            output_path=out,
            prompt=prompt,
        ))
    return packets


def run_review_pass(workspace: Path, chapter_id: str,
                    personas: list[str] | None = None,
                    dispatcher: Callable[[DispatchPacket], None] | None = None) -> AggregatedReview:
    packets = prepare_dispatch_packets(workspace, chapter_id, personas=personas)
    if dispatcher is not None:
        for packet in packets:
            dispatcher(packet)
    return aggregate_reviews(workspace, chapter_id)
