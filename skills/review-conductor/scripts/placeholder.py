"""Shared placeholder-text detection for parsed review findings.

A single source of truth so aggregate_panel and outcomes_loader cannot drift.
"""
from __future__ import annotations

_PLACEHOLDER_TEXTS = {"_(none)_", "(none)", "_none_", "none"}


def is_placeholder(text: str) -> bool:
    stripped = text.strip().lower().strip("_*-").strip()
    return stripped in {"(none)", "none"} or text.strip() in _PLACEHOLDER_TEXTS
