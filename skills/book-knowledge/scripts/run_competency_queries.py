"""Run SPARQL competency queries against the workspace dataset."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Dataset

from .workspace import WorkspaceLayout

_ASSETS_ROOT = Path(__file__).resolve().parent.parent / "assets"

QUERY_CLASSES = ("coverage", "consistency", "defeasible")


def discover_queries(assets_root: Path) -> list[tuple[str, str, Path]]:
    """Returns (class, name, path) for every .rq under assets/queries/."""
    base = assets_root / "queries"
    out: list[tuple[str, str, Path]] = []
    for cls in QUERY_CLASSES:
        cls_dir = base / cls
        if not cls_dir.exists():
            continue
        for f in sorted(cls_dir.glob("*.rq")):
            out.append((cls, f.stem, f))
    # Back-compat: flat .rq files at the top of queries/.
    for f in sorted(base.glob("*.rq")):
        out.append(("coverage", f.stem, f))
    return out


def _load_dataset(layout: WorkspaceLayout) -> Dataset:
    ds = Dataset(default_union=True)
    if layout.dataset.exists() and layout.dataset.stat().st_size > 0:
        ds.parse(layout.dataset, format="trig")
    return ds


def run_competency_queries(layout: WorkspaceLayout) -> dict:
    ds = _load_dataset(layout)
    findings: dict[str, list[tuple]] = {}
    for _cls, name, query_path in discover_queries(_ASSETS_ROOT):
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
