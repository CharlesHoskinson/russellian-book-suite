"""book-compose's wrapper around book-review and review-conductor.

Stage 7 of the book-compose pipeline. The existing `prepare_packets` /
`aggregate` functions remain a thin wrapper over book-review for callers
that want raw access. A new `run_panel` delegates to review-conductor's
seven-persona chapter-default panel for full panel orchestration with
per-persona severity gates.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from .sibling_skills import (
    load_book_review_module,
    load_review_conductor_module,
    review_conductor_root,
)


def prepare_packets(workspace: Path, chapter_id: str,
                    personas: list[str] | None = None) -> list[Any]:
    review_pass = load_book_review_module("review_pass")
    return review_pass.prepare_dispatch_packets(workspace, chapter_id, personas=personas)


def aggregate(workspace: Path, chapter_id: str) -> Any:
    aggregate_mod = load_book_review_module("aggregate_reviews")
    return aggregate_mod.aggregate_reviews(workspace, chapter_id)


def _resolve_panel_path(panel_id: str, workspace: Path | None = None) -> Path:
    """Find a panel YAML. Workspace overlay wins; then installed conductor's panels/."""
    if workspace is not None:
        overlay = Path(workspace) / "qa" / "panels" / f"{panel_id}.yaml"
        if overlay.is_file():
            return overlay
    shipped = review_conductor_root() / "panels" / f"{panel_id}.yaml"
    if not shipped.is_file():
        raise FileNotFoundError(f"panel not found: {panel_id} (looked in workspace overlay and {shipped})")
    return shipped


def run_panel(
    workspace: Path,
    chapter_id: str,
    panel_id: str = "chapter-default",
    dispatcher: Optional[Callable[[Any], None]] = None,
) -> dict:
    """Run the full panel via review-conductor. Returns the verdict dict.

    The conductor loads the panel YAML, builds packets (one per persona),
    invokes the caller-supplied dispatcher once per packet, then aggregates
    findings into chapters/drafts/<chapter_id>/panel-review.md plus
    chapters/drafts/<chapter_id>/verdict.json. Soft-gate semantics live in
    the panel config; book-compose's caller reads verdict["verdict"] to
    decide whether to redraft or proceed.
    """
    conductor = load_review_conductor_module("conductor")
    panel_path = _resolve_panel_path(panel_id, workspace)
    return conductor.run_panel(
        workspace=workspace,
        chapter_id=chapter_id,
        panel_path=panel_path,
        dispatcher=dispatcher,
    )
