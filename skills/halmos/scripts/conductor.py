"""Public entrypoint: run_halmos(workspace, chapter_id, dispatcher) -> verdict dict."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Callable, Optional

from scripts.concept_ledger import build_concept_ledger
from scripts.build_linkage import build_linkage
from scripts.dispatch_halmos_review import dispatch_halmos_review
from scripts.aggregate_halmos import aggregate_halmos


def run_halmos(workspace: Path, chapter_id: str,
               dispatcher: Optional[Callable[[dict], dict]] = None,
               seed_path: Optional[Path] = None) -> dict:
    workspace = Path(workspace)
    build_concept_ledger(workspace, seed_path=seed_path)
    linkage = build_linkage(workspace, chapter_id)
    agent_findings = dispatch_halmos_review(workspace, chapter_id, dispatcher=dispatcher)
    verdict_path = aggregate_halmos(workspace, chapter_id, agent_findings, linkage)
    return json.loads(verdict_path.read_text(encoding="utf-8"))
