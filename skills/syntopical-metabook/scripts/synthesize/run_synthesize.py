"""Full synthesize pipeline: topic_map → disputed_questions → concept_reconciliation.

Convenience entry point for running all synthesize steps in sequence.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SynthesizeResult:
    topic_map_path: Path | None = None
    disputed_question_paths: list[Path] = field(default_factory=list)
    reconciliation_paths: list[Path] = field(default_factory=list)


def run_synthesize(workspace_root: Path, chapter_id: str) -> SynthesizeResult:
    """Run the full synthesize pipeline end-to-end.

    Steps: build_topic_map → build_disputed_questions → build_concept_reconciliation.
    Returns a SynthesizeResult bundling outputs of each stage.
    """
    from scripts.synthesize.topic_map import build_topic_map
    from scripts.synthesize.disputed_questions import build_disputed_questions
    from scripts.synthesize.concept_reconcile import build_concept_reconciliation

    topic_map_path = build_topic_map(workspace_root, chapter_id)
    disputed_paths = build_disputed_questions(workspace_root)
    reconciliation_paths = build_concept_reconciliation(workspace_root)

    return SynthesizeResult(
        topic_map_path=topic_map_path,
        disputed_question_paths=disputed_paths,
        reconciliation_paths=reconciliation_paths,
    )
