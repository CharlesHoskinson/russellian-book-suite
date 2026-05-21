"""Append verified candidates to russellian-style index.json; regenerate corpus-map.md.

The pipeline carries a fat candidate object (paragraph_text, source_url, content_locator,
rhetorical_move_tag, calibration_lesson). The committed index entry schema is narrower
(id, source, line_hint, rhetorical_move, tags, content_locator). This stage projects fat
candidates down to the committed schema, preserving content_locator as an additive field.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.corpus_io import append_index_entries, read_index


def _project_candidate_to_index_entry(cand: dict[str, Any]) -> dict[str, Any]:
    """Project a fat verified candidate to the committed index entry schema."""
    parsed_id = cand["candidate_id"].split("-")
    # Allow IDs like "problems-051" or "external-world-007"; reconstruct integer suffix.
    numeric_suffix = parsed_id[-1]
    source_id = "-".join(parsed_id[:-1])
    return {
        "id": f"{source_id}-{numeric_suffix}",
        "source": source_id,
        "line_hint": cand["line_hint"],
        "rhetorical_move": cand["calibration_lesson"],
        "tags": [cand["rhetorical_move_tag"]],
        "content_locator": cand["content_locator"],
    }


def append_verified_to_index(*, verified_path: Path, index_path: Path) -> None:
    """Read verified.jsonl, project to index schema, append to index.json."""
    new_entries: list[dict[str, Any]] = []
    with verified_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            new_entries.append(_project_candidate_to_index_entry(json.loads(line)))
    append_index_entries(index_path, new_entries)


def regenerate_corpus_map(*, index_path: Path, out_path: Path) -> None:
    """Emit references/russell-corpus-map.md from index.json."""
    idx = read_index(index_path)
    lines = [
        "# Russell Corpus Map",
        "",
        "Auto-generated from `assets/russell-corpus/index.json`. Do not hand-edit.",
        "",
        f"Total entries: {idx['paragraph_count']}",
        "",
        "## Source Mix",
        "",
        "| Source ID | Title | URL |",
        "| --- | --- | --- |",
    ]
    for sid, meta in idx["sources"].items():
        lines.append(f"| `{sid}` | *{meta['title']}* | {meta['url']} |")
    lines += [
        "",
        "## Paragraph Register",
        "",
        "| ID | Source | Line Hint | Rhetorical Move / Lesson | Tags |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in idx["paragraphs"]:
        tags = ", ".join(f"`{t}`" for t in entry.get("tags", []))
        lines.append(
            f"| `{entry['id']}` | {entry['source']} | {entry['line_hint']} | {entry['rhetorical_move']} | {tags} |"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
