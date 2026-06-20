"""Stage-2 per-chapter QA orchestrator.

Prepares a self-contained dispatch payload for one chapter so the host
runtime (Claude / Task tool) can spawn a fresh-context subagent against the
15-item editorial checklist.  Does not itself spawn agents; that is the
host's responsibility.

Backend matrix:
    --llm-backend subagent (default): writes JSON payloads to
        <workspace>/qa/chapter-payloads/<ch-NN>.json. Does NOT execute the
        LLM. The controlling agent consumes the payloads via Task-tool
        dispatch. This is the PAYLOAD_ONLY mode for this skill.
    --llm-backend ollama: not yet supported (this stage's outputs are
        designed for fresh-context subagent review). Exits with code 2.

Layout assumptions (book-compose convention):

    <workspace>/chapters/drafts/ch-NN/draft.md
    <skill-root>/checklists/chapter-qa.md
    <skill-root>/checklists/house-style.yaml

Usage:
    python -m scripts.dispatch_chapter_qa <workspace> [ch-NN ...]
        [--llm-backend {subagent|ollama}] [--model MODEL] [--num-predict N]

When chapter ids are omitted, every chapter draft on disk is prepared.
Each payload is written to ``<workspace>/qa/chapter-payloads/<ch-NN>.json``
so the host can pick them up. Re-running overwrites idempotently.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

SKILL_ROOT = Path(__file__).resolve().parent.parent
CHECKLIST_PATH = SKILL_ROOT / "checklists" / "chapter-qa.md"
HOUSE_STYLE_PATH = SKILL_ROOT / "checklists" / "house-style.yaml"

CH_ID_RE = re.compile(r"^ch-\d{2}$")

# Contract stage marker (set by book-compose's terminal Feynman pass). A chapter
# whose contract declares stage == "feynman-final" was deliberately rewritten in
# Feynman's conversational register: short, varied paragraphs, direct address,
# rhetorical questions, contractions. The register-sensitive Stage-2 checklist
# items C10 (paragraph-length variance) and C11 (Russell-style discipline) would
# otherwise penalise that style, so the agent must relax them. The contract is
# read inline (no book-compose import) to keep book-qa standalone.
FEYNMAN_FINAL_STAGE = "feynman-final"


@dataclass
class ChapterQAPayload:
    """Self-contained dispatch packet for one chapter QA subagent."""

    chapter_id: str
    chapter_path: str
    chapter_text: str
    checklist_text: str
    house_style: dict[str, Any]
    output_path: str
    meta: dict[str, Any] = field(default_factory=dict)


def _load_house_style() -> dict[str, Any]:
    """Return parsed house-style.yaml as a dict (empty if missing)."""
    if not HOUSE_STYLE_PATH.exists():
        return {}
    return yaml.safe_load(HOUSE_STYLE_PATH.read_text(encoding="utf-8")) or {}


def _load_checklist() -> str:
    """Return the raw 15-item editorial checklist markdown."""
    return CHECKLIST_PATH.read_text(encoding="utf-8")


def _read_chapter_stage(workspace: Path, chapter_id: str) -> str | None:
    """Return the contract ``stage`` for one chapter, or None.

    Reads ``<workspace>/chapters/contracts/<ch-NN>.yaml`` inline (no
    book-compose import) so book-qa stays standalone. A missing contract,
    unreadable file, or absent ``stage`` field all yield None — the default
    (Russell) gating regime. Only a string ``stage`` is returned.
    """
    contract_path = workspace / "chapters" / "contracts" / f"{chapter_id}.yaml"
    if not contract_path.exists():
        return None
    try:
        record = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(record, dict):
        return None
    stage = record.get("stage")
    return stage if isinstance(stage, str) else None


def _discover_chapters(workspace: Path) -> list[str]:
    """Return sorted ch-NN ids that have a draft.md on disk."""
    drafts_dir = workspace / "chapters" / "drafts"
    if not drafts_dir.exists():
        return []
    found = []
    for child in drafts_dir.iterdir():
        if child.is_dir() and CH_ID_RE.match(child.name) and (child / "draft.md").exists():
            found.append(child.name)
    return sorted(found)


def prepare_chapter_payload(workspace: Path,
                             chapter_id: str,
                             checklist_text: str | None = None,
                             house_style: dict[str, Any] | None = None) -> ChapterQAPayload:
    """Build the dispatch payload for one chapter.

    The returned object is JSON-serialisable (via ``asdict``) and contains
    everything a fresh-context agent needs: chapter prose, checklist
    rules, canonical-term list, and the path it should write tickets to.
    """
    if not CH_ID_RE.match(chapter_id):
        raise ValueError(f"chapter_id must be 'ch-NN', got {chapter_id!r}")
    draft = workspace / "chapters" / "drafts" / chapter_id / "draft.md"
    if not draft.exists():
        raise FileNotFoundError(draft)
    out_dir = workspace / "qa" / "chapter-tickets"
    out_dir.mkdir(parents=True, exist_ok=True)
    # "stage" here is the QA pipeline stage (2); the contract's editorial stage
    # is threaded under a distinct key so the two never collide.
    meta: dict[str, Any] = {"stage": 2, "checklist_items": 15}
    chapter_stage = _read_chapter_stage(workspace, chapter_id)
    if chapter_stage is not None:
        meta["chapter_stage"] = chapter_stage
        if chapter_stage == FEYNMAN_FINAL_STAGE:
            # Signal the Stage-2 agent to relax the register-sensitive checks
            # (C10 paragraph-length variance, C11 Russell-style discipline) that
            # a Feynman-final chapter legitimately violates. Integrity checks
            # (C1-C9, C12-C15) stay fully enforced.
            meta["relax_register_checks"] = True
    return ChapterQAPayload(
        chapter_id=chapter_id,
        chapter_path=str(draft),
        chapter_text=draft.read_text(encoding="utf-8"),
        checklist_text=checklist_text if checklist_text is not None else _load_checklist(),
        house_style=house_style if house_style is not None else _load_house_style(),
        output_path=str(out_dir / f"{chapter_id}.json"),
        meta=meta,
    )


def prepare_all_payloads(workspace: Path,
                          chapter_ids: list[str] | None = None,
                          shuffle: bool = True,
                          seed: int | None = None) -> list[ChapterQAPayload]:
    """Prepare payloads for many chapters and write them to disk.

    Dispatch order is randomised by default to defeat the position-in-batch
    correlation that the retrospective documented.  Pass ``shuffle=False``
    for deterministic test runs.
    """
    if chapter_ids is None:
        chapter_ids = _discover_chapters(workspace)
    checklist = _load_checklist()
    style = _load_house_style()
    payloads = [prepare_chapter_payload(workspace, cid, checklist, style)
                for cid in chapter_ids]
    if shuffle:
        rng = random.Random(seed)
        rng.shuffle(payloads)
    payload_dir = workspace / "qa" / "chapter-payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)
    for p in payloads:
        (payload_dir / f"{p.chapter_id}.json").write_text(
            json.dumps(asdict(p), indent=2), encoding="utf-8")
    return payloads


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="dispatch_chapter_qa.py",
        description="Stage-2 per-chapter QA payload preparer.",
    )
    parser.add_argument("workspace", help="Path to the book workspace root.")
    parser.add_argument(
        "chapter_ids",
        nargs="*",
        metavar="ch-NN",
        help="Chapter ids to prepare (default: all discovered).",
    )
    parser.add_argument(
        "--llm-backend",
        choices=["subagent", "ollama"],
        default="subagent",
        help=(
            "Backend capability matrix: "
            "subagent — PAYLOAD_ONLY; writes JSON payloads to "
            "<workspace>/qa/chapter-payloads/. Does NOT execute the LLM. "
            "The controlling agent consumes payloads via Task-tool dispatch. "
            "ollama — UNSUPPORTED; this stage's outputs are designed for "
            "fresh-context subagent review. Exits with code 2."
        ),
    )
    parser.add_argument("--model", default="gemma4:31b",
                        help="Ollama model (only used when --llm-backend=ollama).")
    parser.add_argument(
        "--num-predict",
        type=int,
        default=None,
        help="Caps Ollama output tokens (only used when --llm-backend=ollama).",
    )
    args = parser.parse_args(argv[1:])

    if args.llm_backend == "ollama":
        print(
            "[dispatch_chapter_qa] --llm-backend ollama is unsupported for this stage — "
            "this stage prepares payloads for subagent dispatch only.",
            file=sys.stderr,
        )
        return 2

    workspace = Path(args.workspace).resolve()
    chapter_ids = args.chapter_ids or None
    payloads = prepare_all_payloads(workspace, chapter_ids)
    print(f"Prepared {len(payloads)} chapter QA payload(s) at "
          f"{workspace / 'qa' / 'chapter-payloads'}")
    for p in payloads:
        size_kb = len(json.dumps(asdict(p))) / 1024
        print(f"  {p.chapter_id}: {size_kb:.1f} KB -> {p.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
