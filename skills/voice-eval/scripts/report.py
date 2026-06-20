# skills/voice-eval/scripts/report.py
"""20×20 success criterion + Markdown report (REQ-VEVAL-015)."""
from __future__ import annotations

from pathlib import Path


def evaluate_success(*, floor: dict, deltas: dict, winrate: dict, trust: dict, drift: dict) -> dict:
    overall = deltas["overall"]
    criteria = {
        "floor_clean": bool(floor["all_clean"]),
        "signals_higher": all(v > 0 for v in overall.values()) and len(overall) > 0,
        "wins_majority": winrate["rate"] > 0.5,
        "trust_not_worse": trust["v2_minus_v1"] >= 0,
        "lower_drift": drift["v2_mean_cosine"] < drift["v1_mean_cosine"],
    }
    return {"passed": all(criteria.values()), "criteria": criteria}


def render_report(verdict: dict, data: dict, out_path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    status = "PASS" if verdict["passed"] else "FAIL"
    wr = data["winrate"]
    lines = [
        "# HFR v2 — 20×20 report",
        "",
        f"**Result: {status}**",
        "",
        "## Success criteria",
        "",
        "| criterion | met |",
        "|---|---|",
    ]
    for k, ok in verdict["criteria"].items():
        lines.append(f"| {k} | {'yes' if ok else 'NO'} |")
    lines += [
        "",
        "## Pairwise win-rate (v2)",
        "",
        f"- rate: {wr['rate']:.3f}  (n={wr['n']}, 95% CI {wr['ci_low']:.3f}–{wr['ci_high']:.3f})",
        "",
        "## Per-signal mean delta (v2 − v1)",
        "",
        "| signal | delta |",
        "|---|---:|",
    ]
    for sig, d in data["deltas"]["overall"].items():
        lines.append(f"| {sig} | {d:+.3f} |")
    lines += [
        "",
        "## Formula drift (mean within-arm structural cosine; lower is better)",
        "",
        f"- v1: {data['drift']['v1_mean_cosine']:.3f}",
        f"- v2: {data['drift']['v2_mean_cosine']:.3f}",
        "",
    ]
    if not data["floor"]["all_clean"]:
        lines.append(f"> ⚠ floor failures pending regeneration: {data['floor']['failures']}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
