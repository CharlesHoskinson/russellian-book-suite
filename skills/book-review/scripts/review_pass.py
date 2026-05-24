"""Orchestrator for multi-persona chapter review.

The orchestrator does NOT directly invoke a subagent. It prepares fully-rendered
dispatch packets (prompt + I/O paths) that the calling Claude consumes by issuing
one Task-tool call per packet. After all subagent reports are written,
run_review_pass calls aggregate_reviews to produce persona-review.md.

For testability, run_review_pass accepts an injectable dispatcher callable.

CLI usage (--llm-backend ollama only):
    python -m scripts.review_pass --chapter-id ch-01 --draft-path draft.md \\
        --output-dir reviews/ --llm-backend ollama [--model gemma4:31b] \\
        [--num-predict 2048] [--persona gottlieb]
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from .aggregate_reviews import aggregate_reviews, AggregatedReview
from .dispatch_review import render_prompt
from .persona_loader import load_all, load_persona, list_personas


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="review_pass",
        description=(
            "Script-driven entry point for multi-persona chapter review. "
            "Only --llm-backend ollama is self-executable from this script; "
            "the subagent backend is driven by the controlling Claude via Task-tool dispatch."
        ),
    )
    parser.add_argument(
        "--chapter-id",
        required=True,
        help="Chapter identifier, e.g. ch-01",
    )
    parser.add_argument(
        "--draft-path",
        required=True,
        type=Path,
        help="Path to the chapter draft markdown file",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where persona-review-<persona>.md files will be written",
    )
    parser.add_argument(
        "--persona",
        default=None,
        help="Run only this persona ID (default: run all personas in the panel)",
    )
    parser.add_argument(
        "--llm-backend",
        choices=["subagent", "ollama"],
        default="subagent",
        help=(
            "Dispatch backend. 'subagent' is invoked by the controlling Claude "
            "via Task-tool packets and cannot be self-dispatched from this script. "
            "'ollama' uses run_persona_via_ollama for local-LLM dispatch."
        ),
    )
    parser.add_argument(
        "--model",
        default="gemma4:31b",
        help="Ollama model to use (only relevant with --llm-backend ollama)",
    )
    parser.add_argument(
        "--num-predict",
        type=int,
        default=None,
        help=(
            "Max tokens for ollama to generate. "
            "Defaults to persona frontmatter recommended_num_predict or 2048."
        ),
    )
    return parser


def _main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.llm_backend == "subagent":
        print(
            "[review_pass] --llm-backend subagent is invoked by the controlling Claude "
            "via Task-tool dispatch packets; this script cannot self-dispatch. "
            "Use --llm-backend ollama for script-driven local-LLM dispatch.",
            file=sys.stderr,
        )
        return 2

    # --llm-backend ollama
    from llm_infra import run_persona_via_ollama

    SKILL_ROOT = Path(__file__).resolve().parent.parent
    TEMPLATE_PATH = SKILL_ROOT / "assets" / "persona-prompt-template.md"
    PERSONAS_DIR = SKILL_ROOT / "personas"

    draft_path = args.draft_path
    if not draft_path.is_file():
        print(f"[review_pass] draft not found: {draft_path}", file=sys.stderr)
        return 1
    draft_md = draft_path.read_text(encoding="utf-8")
    chapter_id = args.chapter_id

    if args.persona:
        persona_ids = [args.persona]
    else:
        persona_ids = list_personas()

    if not persona_ids:
        print(f"[review_pass] no personas found in {PERSONAS_DIR}", file=sys.stderr)
        return 1

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    exit_code = 0
    for persona_id in persona_ids:
        persona = load_persona(persona_id)
        output_path = output_dir / f"persona-review-{persona_id}.md"
        slots = {
            "persona_body": persona.body_md,
            "display_name": persona.display_name,
            "role": persona.role,
            "persona_id": persona_id,
            "chapter_id": chapter_id,
            "chapter_title": "",
            "chapter_purpose": "",
            "audience": "",
            "draft_md": draft_md,
            "output_path": str(output_path),
        }
        result = run_persona_via_ollama(
            persona_id=persona_id,
            template_path=TEMPLATE_PATH,
            persona_path=PERSONAS_DIR / f"{persona_id}.md",
            slots=slots,
            output_path=output_path,
            model=args.model,
            num_predict=args.num_predict,
        )
        print(
            f"[review_pass] {persona_id}: {result.elapsed_seconds:.1f}s "
            f"-> {result.artifact_path}"
        )

    return exit_code


if __name__ == "__main__":
    sys.exit(_main())
