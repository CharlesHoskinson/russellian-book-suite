"""Run SPARQL competency queries against the workspace dataset."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Dataset

from .workspace import WorkspaceLayout

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "queries"


def _load_dataset(layout: WorkspaceLayout) -> Dataset:
    ds = Dataset(default_union=True)
    if layout.dataset.exists() and layout.dataset.stat().st_size > 0:
        ds.parse(layout.dataset, format="trig")
    return ds


def run_competency_queries(layout: WorkspaceLayout) -> dict:
    ds = _load_dataset(layout)
    findings: dict[str, list[tuple]] = {}
    for query_path in sorted(ASSETS.glob("*.rq")):
        name = query_path.stem
        rows = list(ds.query(query_path.read_text(encoding="utf-8")))
        findings[name] = [tuple(str(v) if v is not None else "" for v in row) for row in rows]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = layout.graph_reports / f"competency-{timestamp}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Competency Query Report — {timestamp}\n"]
    for name, rows in findings.items():
        lines.append(f"## {name}\n")
        if rows:
            for row in rows:
                lines.append(f"- {row}")
        else:
            lines.append("_(no rows)_")
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: run_competency_queries.py <workspace-dir>", file=sys.stderr)
        return 2
    layout = WorkspaceLayout(Path(argv[1]))
    findings = run_competency_queries(layout)
    for name, rows in findings.items():
        print(f"{name}: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
