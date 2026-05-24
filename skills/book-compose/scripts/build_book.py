"""Orchestrate book-level release: preflight -> assemble -> render -> manifest."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .book_preflight import book_preflight
from .book_summary import build_book_summary
from .render_book_html import write_html_skeleton
from .sibling_skills import load_book_knowledge_module
from ._playwright_check import is_playwright_ready


class BookBuildError(Exception):
    pass


def _autodetect_latest_versions(workspace: Path) -> dict[str, str]:
    releases_dir = Path(workspace) / "chapters" / "releases"
    if not releases_dir.is_dir():
        return {}
    by_chapter: dict[str, list[tuple[str, float]]] = {}
    for entry in releases_dir.iterdir():
        if not entry.is_dir():
            continue
        match = re.match(r"^(ch-\d+)-(.+)$", entry.name)
        if not match:
            continue
        chapter_id, version = match.group(1), match.group(2)
        mtime = entry.stat().st_mtime
        by_chapter.setdefault(chapter_id, []).append((version, mtime))
    out: dict[str, str] = {}
    for chapter_id, candidates in by_chapter.items():
        candidates.sort(key=lambda t: t[1], reverse=True)
        out[chapter_id] = candidates[0][0]
    return out


def _assemble_manuscript(workspace: Path, chapter_versions: dict[str, str],
                         book_title: str) -> str:
    from .chapter_contract import load_contract
    lines: list[str] = [f"# {book_title}", ""]
    lines.append(f"_Compiled {datetime.now(timezone.utc).strftime('%Y-%m-%d')}_")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Table of Contents")
    lines.append("")
    sorted_chapters = sorted(chapter_versions.items(), key=lambda kv: int(kv[0].split("-")[1]))
    contracts_dir = Path(workspace) / "chapters" / "contracts"
    titles: dict[str, str] = {}
    for chapter_id, _ in sorted_chapters:
        contract = load_contract(contracts_dir / f"{chapter_id}.yaml")
        titles[chapter_id] = contract["title"]
    for chapter_id, _ in sorted_chapters:
        n = int(chapter_id.split("-")[1])
        lines.append(f"{n}. {titles[chapter_id]}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for chapter_id, version in sorted_chapters:
        n = int(chapter_id.split("-")[1])
        title = titles[chapter_id]
        release_dir = Path(workspace) / "chapters" / "releases" / f"{chapter_id}-{version}"
        body = (release_dir / "draft.md").read_text(encoding="utf-8")
        body_lines = body.splitlines()
        for i, raw in enumerate(body_lines):
            if raw.startswith("# "):
                body_lines[i] = f"# Chapter {n}: {title}"
                break
        lines.append("\n".join(body_lines).strip())
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def _copy_chapter_bundles(workspace: Path, chapter_versions: dict[str, str], book_dir: Path) -> None:
    bundles_dir = book_dir / "chapter-bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    for chapter_id, version in chapter_versions.items():
        src = Path(workspace) / "chapters" / "releases" / f"{chapter_id}-{version}"
        dst = bundles_dir / f"{chapter_id}-{version}"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def _write_claims_bibliography(workspace: Path, summary: dict, book_dir: Path) -> None:
    ledger_mod = load_book_knowledge_module("ledger")
    workspace_mod = load_book_knowledge_module("workspace")
    layout = workspace_mod.WorkspaceLayout(Path(workspace))
    latest = {r["claim_id"]: r for r in ledger_mod.read_claims(layout)}
    cited_chapters = {c["chapter_id"] for c in summary["chapters"]}
    cited_claims = [
        rec for rec in latest.values()
        if rec["status"] == "verified"
        and any(ch in cited_chapters for ch in rec.get("supports_chapters", []))
    ]
    out_path = book_dir / "claims-bibliography.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in sorted(cited_claims, key=lambda r: r["claim_id"]):
            fh.write(json.dumps(rec, sort_keys=True) + "\n")


def _write_manifest(book_dir: Path, version: str, summary: dict, outputs: list[str],
                    chapter_versions: dict[str, str], shacl_conforms: bool,
                    competency_clean: bool) -> None:
    manifest = {
        "book_id": summary["book_id"],
        "title": summary["book_title"],
        "version": version,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chapters_included": [c["chapter_id"] for c in summary["chapters"]],
        "chapter_versions": chapter_versions,
        "outputs": outputs,
        "total_word_count": summary["total_words"],
        "total_claim_count": summary["total_claims"],
        "shacl_conforms": shacl_conforms,
        "competency_clean": competency_clean,
        "sources_bibliography": summary["sources_bibliography"],
    }
    (book_dir / "book-manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=True),
                                                  encoding="utf-8")


def build_book(workspace: Path, version: str,
               chapter_versions: dict[str, str] | None = None,
               book_title: str = "Book", book_id: str = "book") -> Path:
    """Assemble a book-level release."""
    workspace = Path(workspace).resolve()
    if chapter_versions is None:
        chapter_versions = _autodetect_latest_versions(workspace)
    if not chapter_versions:
        raise BookBuildError(f"no chapter releases found at {workspace}")

    pre = book_preflight(workspace, chapter_versions)
    if not pre.passes:
        raise BookBuildError(
            f"book preflight failed; see {pre.report_path}: {pre.issues}"
        )

    book_dir = workspace / "book" / "releases" / version
    book_dir.mkdir(parents=True, exist_ok=True)

    manuscript_md = _assemble_manuscript(workspace, chapter_versions, book_title)
    (book_dir / "manuscript.md").write_text(manuscript_md, encoding="utf-8")

    summary = build_book_summary(workspace, chapter_versions,
                                 book_title=book_title, book_id=book_id)
    (book_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    write_html_skeleton(book_dir / "manuscript.html", summary, manuscript_md)

    outputs = ["manuscript.md", "manuscript.html"]
    pdf_path = book_dir / "manuscript.pdf"
    if is_playwright_ready():
        from .print_pdf import print_pdf
        try:
            print_pdf(book_dir / "manuscript.html", pdf_path)
            outputs.append("manuscript.pdf")
        except Exception as e:
            print(f"warning: PDF render failed: {e}")

    _copy_chapter_bundles(workspace, chapter_versions, book_dir)
    _write_claims_bibliography(workspace, summary, book_dir)
    _write_manifest(book_dir, version, summary, outputs, chapter_versions,
                    pre.shacl_conforms,
                    pre.unsupported_claims == 0 and pre.contradictions == 0)

    return book_dir


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="build_book",
        description="Orchestrate book-level release: preflight -> assemble -> render -> manifest.",
    )
    parser.add_argument("workspace", type=Path, help="Workspace root directory.")
    parser.add_argument("version", help="Release version string (e.g. '1.0.0').")
    parser.add_argument("book_title", help="Human-readable book title.")
    parser.add_argument("book_id", help="Machine-readable book identifier slug.")
    parser.add_argument(
        "chapter_versions_json",
        nargs="?",
        default=None,
        help="Optional path to a JSON file mapping chapter_id -> version. "
             "When omitted, the latest release for each chapter is auto-detected.",
    )
    args = parser.parse_args(argv)

    chapter_versions = None
    if args.chapter_versions_json is not None:
        chapter_versions = json.loads(Path(args.chapter_versions_json).read_text(encoding="utf-8"))

    book_dir = build_book(
        args.workspace, args.version, chapter_versions, args.book_title, args.book_id,
    )
    print(f"book release written to {book_dir}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
