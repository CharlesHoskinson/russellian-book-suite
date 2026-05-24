"""CLI entry point for the v0.3 Synthesize sub-workflow.

The Synthesize sub-workflow (topic_map, concept_reconcile, disputed_questions,
citation_linter) is scaffolded but inactive in v0.2.  It is scheduled for a
v0.3 revisit and will consume LLM (via production_llm or llm_infra) for
concept-reconciliation prompts and topic-map enrichment.

This __main__ wires the --llm-backend flag so the surface area is consistent
with the other skills when v0.3 work begins.

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
            "Currently inactive — v0.2 ships governance sub-workflow only."
        ),
    )
    parser.add_argument("workspace", type=Path, help="Workspace root.")
    parser.add_argument(
        "--llm-backend",
        choices=["subagent", "ollama"],
        default="subagent",
        help=(
            "LLM dispatch backend. subagent (default): external host consumes "
            "dispatch payloads. ollama: route through llm_infra — not yet "
            "wired for this v0.3 sub-workflow (forward-compat scaffold)."
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

    if args.llm_backend == "ollama":
        from llm_infra import make_ollama_call  # noqa: F401 — import check only
        raise NotImplementedError(
            "v0.3 ollama dispatch not yet implemented; --llm-backend flag is "
            "forward-compat scaffold for when v0.3 Synthesize work begins."
        )

    print(
        "[synthesize] v0.3 Synthesize sub-workflow is not yet active. "
        "Run 'forge govern build <workspace>' for the v0.2 governance sub-workflow.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
