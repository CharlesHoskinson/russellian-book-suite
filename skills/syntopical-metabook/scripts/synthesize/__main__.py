"""CLI entry point for the v0.3 Synthesize sub-workflow.

The Synthesize sub-workflow (topic_map, concept_reconcile, disputed_questions,
citation_linter) is scaffolded but inactive in v0.2.  It is scheduled for a
v0.3 revisit and will consume LLM (via production_llm or llm_infra) for
concept-reconciliation prompts and topic-map enrichment.

Backend matrix (v0.3 scaffold):
    --llm-backend subagent — UNSUPPORTED; this is a v0.3 scaffold. Exits with
        code 2 and an inactive-workflow message.
    --llm-backend ollama — UNSUPPORTED; this is a v0.3 scaffold. Exits with
        code 2 and an inactive-workflow message.

Note: this is a v0.3 scaffold; both --llm-backend subagent and --llm-backend
ollama exit with an inactive-workflow message (exit code 2).

Usage:
    python -m scripts.synthesize <workspace>
        [--llm-backend {subagent|ollama}] [--model MODEL] [--num-predict N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.synthesize",
        description=(
            "v0.3 Synthesize sub-workflow scaffold. "
            "Build topic maps, reconcile concepts, and surface disputed questions. "
            "Currently inactive — v0.2 ships governance sub-workflow only. "
            "Note: this is a v0.3 scaffold; both --llm-backend subagent and "
            "--llm-backend ollama exit with an inactive-workflow message (exit code 2)."
        ),
    )
    parser.add_argument("workspace", type=Path, help="Workspace root.")
    parser.add_argument(
        "--llm-backend",
        choices=["subagent", "ollama"],
        default="subagent",
        help=(
            "Backend capability matrix (v0.3 scaffold): "
            "subagent — UNSUPPORTED; inactive-workflow scaffold, exits with code 2. "
            "ollama — UNSUPPORTED; inactive-workflow scaffold, exits with code 2. "
            "Note: this is a v0.3 scaffold; both backends exit with an "
            "inactive-workflow message."
        ),
    )
    parser.add_argument(
        "--model",
        default="gemma4:31b",
        help="Ollama model (only used when --llm-backend=ollama).",
    )
    parser.add_argument(
        "--num-predict",
        type=int,
        default=None,
        help="Caps Ollama output tokens (only used when --llm-backend=ollama).",
    )
    return parser


def _main(argv: list[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Both subagent and ollama are unsupported for this v0.3 scaffold.
    print(
        f"[synthesize] --llm-backend {args.llm_backend} is unsupported — "
        "v0.3 Synthesize sub-workflow is not yet active (inactive-workflow). "
        "Run 'forge govern build <workspace>' for the v0.2 governance sub-workflow.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
