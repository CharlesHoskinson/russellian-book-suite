"""Build syntopical/topic-map.md: every concept grouped by thesis top-level node.

Per REQ-SYN-1, each row has `{slug, sources, n_verified_claims}`."""
from __future__ import annotations
from pathlib import Path
from scripts.provenance import provenance_footer


def _load_book_knowledge():
    from sibling_skills import load_skill_api
    return load_skill_api("book-knowledge", expected_major=0)


def _load_book_thesis():
    from sibling_skills import load_skill_api
    return load_skill_api("book-thesis", expected_major=0)


def build_topic_map(workspace_root: Path, chapter_id: str) -> Path:
    bk = _load_book_knowledge()
    bt = _load_book_thesis()
    concepts = bk.list_concepts(workspace_root)
    verified = bk.query_claims({"state": "verified"}, workspace_root)
    tree = bt.read_thesis_tree(chapter_id, workspace_root)
    top_nodes = [n for n in tree.nodes if n.parent_id is None]
    # Sort top nodes by node_id for determinism
    top_nodes = sorted(top_nodes, key=lambda n: n.node_id)
    # Index concepts by which thesis-tree top node they belong to (via overlapping tags).
    by_node: dict[str, list] = {n.node_id: [] for n in top_nodes}
    by_node["_unassigned"] = []
    # Sort concepts by slug for determinism
    concepts_sorted = sorted(concepts, key=lambda c: c.slug)
    for c in concepts_sorted:
        n_claims = sum(1 for cl in verified
                       if any(t in cl.tags for t in c.surface_forms + [c.slug]))
        assigned = False
        for n in top_nodes:
            if any(t in n.tags for t in c.surface_forms + [c.slug]):
                by_node[n.node_id].append((c, n_claims))
                assigned = True
                break
        if not assigned:
            by_node["_unassigned"].append((c, n_claims))
    out = workspace_root / "syntopical" / "topic-map.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Topic Map", ""]
    for n in top_nodes:
        lines += [f"## {n.node_id}", "", "| slug | sources | n_verified_claims |", "|---|---|---|"]
        for c, n_cl in by_node[n.node_id]:
            lines.append(f"| {c.slug} | {','.join(sorted(c.sources))} | {n_cl} |")
        lines.append("")
    if by_node["_unassigned"]:
        lines += ["## Unassigned", "", "| slug | sources | n_verified_claims |", "|---|---|---|"]
        for c, n_cl in by_node["_unassigned"]:
            lines.append(f"| {c.slug} | {','.join(sorted(c.sources))} | {n_cl} |")
        lines.append("")
    out.write_text("\n".join(lines) + "\n" + provenance_footer(), encoding="utf-8")
    return out
