"""Audit sampler — emits a 5% random sample for operator review.

The operator runs through `sample.md`, marks each entry accept/reject, and feeds the
decision list into `evaluate_audit_decisions`. If the reject rate exceeds the halt
threshold (default 10%), the pipeline halts and the operator tunes the extractor or
generic-phrases list before re-running the batch.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def sample_audit(
    *,
    verified_path: Path,
    out_path: Path,
    sample_rate: float = 0.05,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Sample `sample_rate` (min 1) of verified.jsonl. Write a human-readable markdown report."""
    rows = []
    with verified_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if not rows:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("# Audit sample\n\nNo entries.\n", encoding="utf-8")
        return []
    n = max(1, round(len(rows) * sample_rate))
    rng = random.Random(seed)
    sampled = rng.sample(rows, k=min(n, len(rows)))
    _write_audit_markdown(sampled, out_path)
    return sampled


def _write_audit_markdown(sampled: list[dict[str, Any]], out_path: Path) -> None:
    parts = ["# Audit sample", "", f"Sampled {len(sampled)} entries.", "",
             "For each entry below, mark `accept` / `reject` / `tag-revise`.", ""]
    for i, entry in enumerate(sampled, start=1):
        parts.append(f"## {i}. `{entry['candidate_id']}`")
        parts.append("")
        parts.append(f"**Tag:** `{entry.get('rhetorical_move_tag', '?')}`")
        parts.append("")
        parts.append(f"**Lesson:** {entry.get('calibration_lesson', '?')}")
        parts.append("")
        parts.append("**Paragraph:**")
        parts.append("")
        parts.append("> " + entry.get("paragraph_text", "").replace("\n", "\n> "))
        parts.append("")
        parts.append("**Decision:** ___")
        parts.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")


@dataclass
class AuditDecision:
    action: str  # "proceed" | "halt"
    reject_rate: float


def evaluate_audit_decisions(decisions: list[str], halt_threshold: float = 0.10) -> AuditDecision:
    """Compute reject rate; halt if it exceeds the threshold."""
    if not decisions:
        return AuditDecision("proceed", 0.0)
    rejects = sum(1 for d in decisions if d == "reject")
    rate = rejects / len(decisions)
    return AuditDecision("halt" if rate > halt_threshold else "proceed", rate)
