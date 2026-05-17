"""REQ-GAP-2: append uncovered thesis-node statements to pending-seeds.txt
so the next Acquire run can use them as seeds.

Reads the most-recent gap report for the chapter to find uncovered node_ids,
then looks up their statements directly from the thesis-tree yaml.
"""
from __future__ import annotations
import re
from pathlib import Path
import yaml
from scripts.acquire.manifest import append_pending_seeds


def _latest_gap_report(workspace_root: Path, chapter_id: str) -> Path | None:
    reports = workspace_root / "syntopical" / "reports"
    if not reports.exists():
        return None
    candidates = sorted(reports.glob(f"gaps-{chapter_id}-*.md"))
    return candidates[-1] if candidates else None


def _uncovered_node_ids(report_path: Path) -> list[str]:
    """Parse the gap report table for node_ids with coverage < 1.0."""
    node_ids: list[str] = []
    for line in report_path.read_text(encoding="utf-8").splitlines():
        # Table data rows: | node_id | score | n |
        m = re.match(r"^\|\s*(\S+)\s*\|\s*([0-9.]+)\s*\|", line)
        if m:
            nid = m.group(1)
            score = float(m.group(2))
            if score < 1.0:
                node_ids.append(nid)
    return node_ids


def _statements_for_nodes(workspace_root: Path, chapter_id: str,
                           node_ids: list[str]) -> list[str]:
    """Read the thesis-tree yaml and return statements for the given node_ids."""
    tree_path = workspace_root / "chapters" / chapter_id / "thesis-tree.yaml"
    if not tree_path.exists():
        return []
    raw = yaml.safe_load(tree_path.read_text(encoding="utf-8")) or {}
    id_set = set(node_ids)
    statements: list[str] = []
    seen: set[str] = set()
    for n in (raw.get("nodes") or []):
        if n.get("node_id") in id_set:
            stmt = (n.get("statement") or "").strip()
            if stmt and stmt not in seen:
                statements.append(stmt)
                seen.add(stmt)
    return statements


def seed_from_gap_report(workspace_root: Path, chapter_id: str,
                         required_per_node: int = 3) -> Path:
    report = _latest_gap_report(workspace_root, chapter_id)
    if report is None:
        out = workspace_root / "syntopical" / "acquisition" / "pending-seeds.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        return out
    node_ids = _uncovered_node_ids(report)
    statements = _statements_for_nodes(workspace_root, chapter_id, node_ids)
    out = workspace_root / "syntopical" / "acquisition" / "pending-seeds.txt"
    append_pending_seeds(out, statements)
    return out
