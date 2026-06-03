"""REQ-GAP-1: compute per-thesis-node coverage and write a gap report."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from scripts.provenance import provenance_footer


def _load_book_knowledge():
    from sibling_skills import load_skill_api
    return load_skill_api("book-knowledge", expected_major=0)


def _load_book_thesis():
    from sibling_skills import load_skill_api
    return load_skill_api("book-thesis", expected_major=0)


def build_coverage_report(workspace_root: Path, chapter_id: str,
                          required_per_node: int = 3) -> Path:
    bk = _load_book_knowledge()
    bt = _load_book_thesis()
    verified = bk.query_claims({"state": "verified"}, workspace_root)
    tree = bt.read_thesis_tree(chapter_id, workspace_root)
    scored: list[tuple[str, float, int]] = []  # (node_id, score, n_supporting)
    for n in tree.nodes:
        supporting = [c for c in verified if any(t in (c.tags or []) for t in (n.tags or []))]
        score = min(1.0, len(supporting) / max(1, required_per_node))
        scored.append((n.node_id, score, len(supporting)))
    uncovered = [(nid, s, k) for nid, s, k in scored if s < 1.0]
    uncovered.sort(key=lambda t: t[1])  # ascending: worst first
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = workspace_root / "syntopical" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"gaps-{chapter_id}-{ts}.md"
    lines = [f"# Gap Report: chapter {chapter_id}", "",
             f"Required supporting claims per node: {required_per_node}", "",
             "| node_id | coverage_score | n_supporting |",
             "|---|---|---|"]
    for nid, s, k in uncovered:
        lines.append(f"| {nid} | {s:.2f} | {k} |")
    avg = (sum(s for _, s, _ in scored) / max(1, len(scored))) if scored else 1.0
    lines += ["", f"average_coverage_score: {avg:.3f}"]
    out.write_text("\n".join(lines) + "\n" + provenance_footer(), encoding="utf-8")
    return out
