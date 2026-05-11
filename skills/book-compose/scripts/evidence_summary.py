"""Per-section list of verified claims cited by a chapter."""
from __future__ import annotations

from pathlib import Path

from .sibling_skills import load_book_knowledge_module


def build_evidence_summary(workspace: Path, chapter_id: str) -> str:
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")

    layout = workspace_mod.WorkspaceLayout(Path(workspace).resolve())
    latest: dict[str, dict] = {}
    for r in ledger_mod.read_claims(layout):
        latest[r["claim_id"]] = r
    relevant = [
        c for c in latest.values()
        if c["status"] == "verified" and chapter_id in c.get("supports_chapters", [])
    ]
    if not relevant:
        return f"# Evidence Summary - {chapter_id}\n\n(No verified claims assigned to {chapter_id}.)\n"
    lines = [f"# Evidence Summary - {chapter_id}", ""]
    for claim in sorted(relevant, key=lambda c: c["claim_id"]):
        lines.append(f"## {claim['claim_id']}")
        lines.append(f"**Canonical text:** {claim['canonical_text']}")
        lines.append(f"**Confidence:** {claim['confidence']}")
        for span in claim["source_spans"]:
            page = span.get("page_index")
            page_part = f" page {page}" if page else ""
            lines.append(f"- Source: `{span['doc_id']}`{page_part} - {span['locator_text']!r}")
        lines.append("")
    return "\n".join(lines)
