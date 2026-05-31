"""Render one Markdown report per induced/defconstraint rule from positions.edn."""
from __future__ import annotations
import argparse
import sys
from collections import defaultdict
from pathlib import Path
from ._positions_io import Position, read_positions
from ._stance import Stance
from .._staleness import check_not_stale


_STANCE_GLYPH = {
    Stance.SUPPORTS:    "supports",
    Stance.CONTRADICTS: "contradicts",
    Stance.SILENT:      "silent",
    Stance.EXTENDS:     "extends",
}


def _evidence_summary(p: Position) -> str:
    if p.declared_by_charter:
        return "declared by charter"
    if p.stance == Stance.SUPPORTS:
        n = len(p.supporting_docs)
        docs = ", ".join(sorted(p.supporting_docs))
        return f"{n} doc(s): {docs}" if docs else "—"
    if p.stance == Stance.CONTRADICTS:
        n = len(p.contradicting_docs)
        docs = ", ".join(sorted(p.contradicting_docs))
        return f"{n} contradicting doc(s): {docs}" if docs else "—"
    if p.stance == Stance.EXTENDS:
        docs = ", ".join(sorted(p.supporting_docs))
        return f"partial support: {docs}"
    return "—"


def _render_one(rule_id: str, rows: list[Position]) -> str:
    rule_form = rows[0].rule_form if rows[0].rule_form else "(rule form not recorded)"
    source = rows[0].source
    induction_prov = rows[0].induction_prov

    lines = [
        f"# Rule `{rule_id}`",
        "",
        f"> {rule_form}",
        "",
        f"**Source:** `{source}`  ",
        f"**Provenance:** `{induction_prov}`",
        "",
        "## Schools",
        "",
        "| School | Stance | Evidence |",
        "|---|---|---|",
    ]
    for p in sorted(rows, key=lambda r: r.school):
        lines.append(f"| {p.school} | {_STANCE_GLYPH[p.stance]} | {_evidence_summary(p)} |")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    for p in sorted(rows, key=lambda r: r.school):
        if not (p.supporting_atoms or p.contradicting_atoms):
            continue
        lines.append(f"### {p.school}")
        for atom in sorted(p.supporting_atoms):
            lines.append(f"- ✓ `{atom}`")
        for atom in sorted(p.contradicting_atoms):
            lines.append(f"- ✗ `{atom}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_per_rule(positions_path: Path, out_dir: Path) -> int:
    positions_path = Path(positions_path)
    ws = positions_path.parents[1]
    check_not_stale(positions_path, [
        ws / "knowledge" / "claims" / "ledger.jsonl",
        ws / "rules" / "booklogic" / "induced-theory.prov.edn",
        ws / "rules" / "constraints.edn",
    ])
    rows = read_positions(positions_path)
    grouped: dict[str, list[Position]] = defaultdict(list)
    for p in rows:
        grouped[p.rule_id].append(p)
    out_dir.mkdir(parents=True, exist_ok=True)
    for rule_id, group in grouped.items():
        safe = rule_id.replace("/", "__").replace(":", "").lstrip(":")
        (out_dir / f"{safe}.md").write_text(
            _render_one(rule_id, group),
            encoding="utf-8", newline="\n",
        )
    return len(grouped)


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.governance.render_per_rule")
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args(argv)
    workspace = args.workspace.resolve()
    n = render_per_rule(
        workspace / "syntopical" / "positions.edn",
        workspace / "syntopical" / "rules",
    )
    print(f"rendered {n} rule report(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
