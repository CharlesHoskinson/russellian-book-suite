# skills/voice-eval/scripts/detector.py
"""Optional AI-detector / perplexity read — advisory only (REQ-VEVAL-014).

Per the design (source-paper correction 3: detectors hit ~0% TPR at 1% FPR and are
trivially evaded), any score here is informational. This module structurally cannot
gate: it returns rows and the constant flags advisory=True, gates=False, and exposes
no pass/fail decision.
"""
from __future__ import annotations

from typing import Callable, Optional


def detector_report(passages: list[dict], *, scorer: Optional[Callable[[str], float]]) -> dict:
    rows = []
    if scorer is not None:
        for p in passages:
            rows.append({"prompt_id": p["prompt_id"], "arm": p["arm"], "score": scorer(p["text"])})
    return {"advisory": True, "gates": False, "rows": rows}
