"""Build the data payload that feeds the interactive HTML browser.

Two phases:
1. Deterministic collection - walks chapter releases, extracts word counts,
   first paragraphs, section headings, and per-chapter claim counts.
2. LLM-assisted abstracting - provides scaffolding (`abstract_seed`) but
   leaves the actual prose abstract for Claude to write during book build.

The script returns a JSON-serializable dict that render_book_html.py inlines
into the React app.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from .chapter_contract import load_contract
from .sibling_skills import load_book_knowledge_module

_HEADING2 = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def _first_paragraph(text: str) -> str:
    body_lines = []
    for raw in text.splitlines():
        if raw.startswith("#"):
            continue
        if raw.strip() == "":
            if body_lines:
                break
            continue
        body_lines.append(raw)
    return " ".join(body_lines).strip()[:400]


def _section_headings(text: str) -> list[str]:
    return [m.group(1).strip() for m in _HEADING2.finditer(text)]


def collect_chapter_data(workspace: Path, chapter_versions: dict[str, str],
                         contracts: dict[str, dict] | None = None) -> list[dict]:
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")
    layout = workspace_mod.WorkspaceLayout(Path(workspace))

    latest_claims: dict[str, dict] = {}
    for r in ledger_mod.read_claims(layout):
        latest_claims[r["claim_id"]] = r

    contracts_dir = Path(workspace) / "chapters" / "contracts"
    records: list[dict] = []
    for chapter_id, version in sorted(chapter_versions.items()):
        if contracts is not None and chapter_id in contracts:
            contract = contracts[chapter_id]
        else:
            contract = load_contract(contracts_dir / f"{chapter_id}.yaml")
        release_dir = Path(workspace) / "chapters" / "releases" / f"{chapter_id}-{version}"
        draft = (release_dir / "draft.md").read_text(encoding="utf-8")
        manifest = yaml.safe_load((release_dir / "manifest.yaml").read_text(encoding="utf-8"))
        chapter_claims = [
            c for c in latest_claims.values()
            if c["status"] == "verified" and chapter_id in c.get("supports_chapters", [])
        ]
        records.append({
            "chapter_id": chapter_id,
            "title": contract["title"],
            "purpose": contract["purpose"],
            "chapter_type": contract["chapter_type"],
            "draft_md": draft,
            "word_count": _word_count(draft),
            "first_paragraph": _first_paragraph(draft),
            "section_headings": _section_headings(draft),
            "claim_count": len(chapter_claims),
            "claim_ids": [c["claim_id"] for c in chapter_claims],
            "release_version": version,
            "release_built_at": manifest.get("built_at", ""),
        })
    return records


def _claim_source_spans(workspace: Path, claim_ids: list[str]) -> list[dict]:
    if not claim_ids:
        return []
    ledger_mod = load_book_knowledge_module("ledger")
    workspace_mod = load_book_knowledge_module("workspace")
    layout = workspace_mod.WorkspaceLayout(Path(workspace))
    latest = {r["claim_id"]: r for r in ledger_mod.read_claims(layout)}
    spans: list[dict] = []
    for cid in claim_ids:
        rec = latest.get(cid)
        if rec:
            spans.extend(rec.get("source_spans", []))
    return spans


def build_book_summary(workspace: Path, chapter_versions: dict[str, str],
                       book_title: str = "Book", book_id: str = "book",
                       contracts: dict[str, dict] | None = None) -> dict:
    chapters = collect_chapter_data(workspace, chapter_versions, contracts=contracts)
    total_words = sum(c["word_count"] for c in chapters)
    total_claims = sum(c["claim_count"] for c in chapters)
    sources = sorted({
        span["doc_id"]
        for c in chapters
        for span in _claim_source_spans(workspace, c["claim_ids"])
    })

    chapters_out = [
        {
            "chapter_id": c["chapter_id"],
            "title": c["title"],
            "purpose": c["purpose"],
            "chapter_type": c["chapter_type"],
            "abstract_seed": c["first_paragraph"],
            "section_headings": c["section_headings"],
            "word_count": c["word_count"],
            "claim_count": c["claim_count"],
            "draft_md": c["draft_md"],
        }
        for c in chapters
    ]

    return {
        "book_id": book_id,
        "book_title": book_title,
        "total_words": total_words,
        "total_claims": total_claims,
        "chapters": chapters_out,
        "sources_bibliography": sources,
    }


def main(argv: list[str]) -> int:
    import sys
    if len(argv) < 3:
        print("usage: book_summary.py <workspace-dir> <chapter_versions.json>", file=sys.stderr)
        return 2
    versions = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    summary = build_book_summary(Path(argv[1]), versions)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv))
