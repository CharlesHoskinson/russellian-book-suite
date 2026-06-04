"""Adversarial review: 'where does the paper take a position contrary to a
cited school without acknowledging it?'
"""
from __future__ import annotations
import argparse
import sys
from collections import defaultdict
from pathlib import Path
from ._positions_io import Position, read_positions
from ._config import GovernanceConfig, load_or_create_config
from ._stance import Stance
from .._staleness import check_positions_fresh


def _render(positions: list[Position], cfg: GovernanceConfig) -> str:
    by_rule: dict[str, list[Position]] = defaultdict(list)
    for p in positions:
        by_rule[p.rule_id].append(p)

    contested: list[tuple[str, Position, list[Position]]] = []
    for rule_id, rows in by_rule.items():
        self_pos = next(
            (r for r in rows if r.school == cfg.self_school), None
        )
        if self_pos is None or self_pos.stance != Stance.SUPPORTS:
            continue
        contradictions = [
            r for r in rows
            if r.school != cfg.self_school and r.stance == Stance.CONTRADICTS
        ]
        if contradictions:
            contested.append((rule_id, self_pos, contradictions))

    lines = [
        "# Adversarial review",
        "",
        f"Positions held by the self-school (`{cfg.self_school}`) that are",
        "contradicted by at least one other cited school. Each line is a",
        "place the paper takes a stance against a school in its bibliography",
        "without acknowledging the divergence.",
        "",
    ]
    if not contested:
        lines.append("**No contested positions** — the self-school's assertions")
        lines.append("are not contradicted by any other school in the ledger.")
        return "\n".join(lines).rstrip() + "\n"

    for rule_id, self_pos, contradictions in sorted(contested):
        lines.append(f"## `{rule_id}`")
        lines.append("")
        if self_pos.rule_form:
            lines.append(f"> {self_pos.rule_form}")
            lines.append("")
        lines.append(f"- `{cfg.self_school}`: **supports** (your position)")
        for c in sorted(contradictions, key=lambda r: r.school):
            lines.append(f"- `{c.school}`: **contradicts**")
        lines.append("")
        lines.append(
            "→ **Action:** acknowledge the divergence in the relevant paper section "
            "and cite the contradicting work."
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_adversarial(positions_path: Path, out_path: Path,
                       config: GovernanceConfig) -> Path:
    check_positions_fresh(positions_path)
    positions = read_positions(positions_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_render(positions, config), encoding="utf-8", newline="\n")
    return out_path


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.governance.render_adversarial")
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args(argv)
    workspace = args.workspace.resolve()
    cfg = load_or_create_config(workspace / "syntopical" / "governance-config.edn")
    out = render_adversarial(
        workspace / "syntopical" / "positions.edn",
        workspace / "syntopical" / "adversarial-review.md",
        cfg,
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
