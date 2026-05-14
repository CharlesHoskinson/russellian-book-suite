"""Build dispatch packets via book-review.prepare_dispatch_packets, with optional
few-shot injection from the outcomes library.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .load_panel import Panel
from .outcomes_loader import load_exemplars, pick_findings, render_few_shot
from .sibling_skills import load_book_review_module


@dataclass(frozen=True)
class PanelPacket:
    persona_id: str
    persona_display_name: str
    chapter_id: str
    draft_path: Path
    output_path: Path
    prompt: str


def build_packets(
    workspace: Path,
    chapter_id: str,
    panel: Panel,
    outcomes_seed: int = 42,
) -> list[PanelPacket]:
    """Build one PanelPacket per persona configured in the panel."""
    review_pass = load_book_review_module("review_pass")
    persona_ids = [p.id for p in panel.personas]
    br_packets = review_pass.prepare_dispatch_packets(
        workspace, chapter_id, personas=persona_ids,
    )

    # Inject few-shot if outcomes are configured.
    few_shot_by_persona: dict[str, str] = {}
    if panel.outcomes.per_persona_exemplars > 0 and panel.outcomes.exemplar_paths:
        # Resolve relative paths against the panel's own location (caller-supplied);
        # the chapter-default.yaml uses ../book-review/references/outcomes/... which
        # is relative to the panel YAML's directory. For test fixtures and
        # absolute paths, use the path as-is.
        exemplar_paths = [Path(p) for p in panel.outcomes.exemplar_paths]
        exemplars = load_exemplars(exemplar_paths)
        picked = pick_findings(
            exemplars,
            per_persona=panel.outcomes.per_persona_exemplars,
            seed=outcomes_seed,
        )
        for persona_id in persona_ids:
            snippet = render_few_shot(persona_id, picked)
            if snippet:
                few_shot_by_persona[persona_id] = snippet

    out: list[PanelPacket] = []
    for br_packet in br_packets:
        prompt = br_packet.prompt
        snippet = few_shot_by_persona.get(br_packet.persona_id)
        if snippet:
            prompt = prompt + "\n\n" + snippet + "\n"
        out.append(PanelPacket(
            persona_id=br_packet.persona_id,
            persona_display_name=br_packet.persona_display_name,
            chapter_id=br_packet.chapter_id,
            draft_path=br_packet.draft_path,
            output_path=br_packet.output_path,
            prompt=prompt,
        ))
    return out
