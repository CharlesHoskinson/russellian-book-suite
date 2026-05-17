"""Project a per-chapter lens from the syntopical layer.

REQ-LENS-1: write syntopical/lenses/<chapter_id>.md containing topic-map rows,
disputed-questions, and concept-reconciliation entries whose tags intersect
the chapter's tags union thesis-tree tags. Plus a Coverage summary.

REQ-LENS-2: section order is exactly `## Topics`, `## Disputed Questions`,
`## Concept Reconciliation`, `## Coverage`. book-compose's read_lens parses
this order strictly.

REQ-LENS-3: YAML frontmatter with chapter_id, generated_at, source_run_id,
n_topics, n_disputed, n_concepts, coverage_score.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import re
import yaml
from scripts.provenance import provenance_footer


def _load_chapter_tags(ws: Path, chapter_id: str) -> set[str]:
    contract = yaml.safe_load((ws / "chapters" / chapter_id / "contract.yaml")
                              .read_text(encoding="utf-8"))
    tags = set(contract.get("tags") or [])
    tree_path = ws / "chapters" / chapter_id / "thesis-tree.yaml"
    if tree_path.exists():
        tree = yaml.safe_load(tree_path.read_text(encoding="utf-8")) or {}
        for n in (tree.get("nodes") or []):
            for t in (n.get("tags") or []):
                tags.add(t)
    return tags


def _filter_topic_map(topic_map_md: str, tags: set[str]) -> tuple[str, int]:
    """Keep table rows whose first column (slug) matches any chapter tag.
    Header row preserved if any data rows pass."""
    if not topic_map_md.strip():
        return "", 0
    lines = topic_map_md.splitlines()
    out_lines: list[str] = []
    header_block: list[str] = []
    data_rows: list[str] = []
    kept = 0

    def _flush():
        nonlocal data_rows, header_block, out_lines, kept
        if header_block and data_rows:
            out_lines.extend(header_block)
            for r in data_rows:
                out_lines.append(r)
                kept += 1
        header_block = []
        data_rows = []

    for line in lines:
        if line.startswith("|"):
            if len(header_block) < 2:
                header_block.append(line)
            else:
                # data row — match first cell against tags
                first_cell = line.split("|", 2)[1].strip()
                if first_cell in tags:
                    data_rows.append(line)
        else:
            _flush()
            out_lines.append(line)
    _flush()
    return "\n".join(out_lines).strip(), kept


def _collect_disputed(ws: Path, tags: set[str]) -> tuple[str, int]:
    d = ws / "syntopical" / "disputed-questions"
    if not d.exists():
        return "", 0
    parts: list[str] = []
    n = 0
    for f in sorted(d.glob("*.md")):
        if f.stem in tags:
            parts.append(f.read_text(encoding="utf-8"))
            n += 1
    return "\n\n".join(parts), n


def _collect_concepts(ws: Path, tags: set[str]) -> tuple[str, int]:
    d = ws / "syntopical" / "concepts"
    if not d.exists():
        return "", 0
    parts: list[str] = []
    n = 0
    for f in sorted(d.glob("*.md")):
        body = f.read_text(encoding="utf-8")
        # Include if the concept slug, or any alternate, matches a tag.
        if f.stem in tags or any(t in body for t in tags):
            parts.append(body)
            n += 1
    return "\n\n".join(parts), n


def _coverage_block(ws: Path, chapter_id: str) -> tuple[str, float]:
    """Pull most-recent gap report for this chapter. If none, coverage = 1.0."""
    reports = ws / "syntopical" / "reports"
    if not reports.exists():
        return "_no gap report available_", 1.0
    candidates = sorted(reports.glob(f"gaps-{chapter_id}-*.md"))
    if not candidates:
        return "_no gap report available_", 1.0
    latest = candidates[-1]
    body = latest.read_text(encoding="utf-8")
    # Extract average coverage from the gap report's footer.
    m = re.search(r"average_coverage_score:\s*([0-9.]+)", body)
    avg = float(m.group(1)) if m else 1.0
    return f"Latest gap report: `{latest.name}` (avg coverage {avg:.2f}).", avg


def project_lens(workspace_root: Path, chapter_id: str, source_run_id: str = "") -> Path:
    tags = _load_chapter_tags(workspace_root, chapter_id)
    tm_path = workspace_root / "syntopical" / "topic-map.md"
    tm_md = tm_path.read_text(encoding="utf-8") if tm_path.exists() else ""
    topics_md, n_topics = _filter_topic_map(tm_md, tags)
    disputed_md, n_disputed = _collect_disputed(workspace_root, tags)
    concepts_md, n_concepts = _collect_concepts(workspace_root, tags)
    coverage_md, coverage_score = _coverage_block(workspace_root, chapter_id)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    fm = {
        "chapter_id": chapter_id,
        "generated_at": generated_at,
        "source_run_id": source_run_id,
        "n_topics": n_topics,
        "n_disputed": n_disputed,
        "n_concepts": n_concepts,
        "coverage_score": coverage_score,
    }
    body = (
        "---\n"
        + yaml.safe_dump(fm, sort_keys=True).strip() + "\n"
        + "---\n\n"
        + "## Topics\n\n" + (topics_md or "_none_") + "\n\n"
        + "## Disputed Questions\n\n" + (disputed_md or "_none_") + "\n\n"
        + "## Concept Reconciliation\n\n" + (concepts_md or "_none_") + "\n\n"
        + "## Coverage\n\n" + coverage_md + "\n"
        + provenance_footer(source_run_id)
    )
    out = workspace_root / "syntopical" / "lenses" / f"{chapter_id}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    return out
