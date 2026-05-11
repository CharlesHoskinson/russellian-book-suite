"""book-compose's wrapper around book-review.

Provides thin functions that book-compose uses to invoke the multi-persona
review machinery owned by the book-review sibling skill.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .sibling_skills import load_book_review_module


def prepare_packets(workspace: Path, chapter_id: str,
                    personas: list[str] | None = None) -> list[Any]:
    review_pass = load_book_review_module("review_pass")
    return review_pass.prepare_dispatch_packets(workspace, chapter_id, personas=personas)


def aggregate(workspace: Path, chapter_id: str) -> Any:
    aggregate_mod = load_book_review_module("aggregate_reviews")
    return aggregate_mod.aggregate_reviews(workspace, chapter_id)
