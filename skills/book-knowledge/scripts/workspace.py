"""Book workspace location, creation, and layout helpers."""
from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SKELETON = ASSETS / "workspace-skeleton"

WORKSPACE_MARKER = "CLAUDE.md"
TOP_LEVEL_DIRS = [
    "raw/pdf", "raw/markdown", "raw/manifests",
    "wiki/sources", "wiki/concepts", "wiki/entities", "wiki/chapters",
    "claims/verification",
    "graph/imports", "graph/reports",
    "chapters/contracts", "chapters/drafts", "chapters/releases",
    "reports",
]
TOP_LEVEL_FILES = [
    ("CLAUDE.md", "CLAUDE.md.template"),
    ("wiki/index.md", "wiki/index.md.template"),
    ("wiki/log.md", "wiki/log.md.template"),
    ("wiki/current-status.md", "wiki/current-status.md.template"),
]
TOP_LEVEL_EMPTY_FILES = [
    "claims/ledger.jsonl",
    "claims/conflicts.jsonl",
    "graph/dataset.trig",
    "graph/shapes.ttl",
]


def init_workspace(target: Path) -> Path:
    """Create a book workspace at target. Idempotent — never overwrites existing files."""
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    for rel in TOP_LEVEL_DIRS:
        (target / rel).mkdir(parents=True, exist_ok=True)

    for dest_rel, src_rel in TOP_LEVEL_FILES:
        dest = target / dest_rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(SKELETON / src_rel, dest)

    for rel in TOP_LEVEL_EMPTY_FILES:
        path = target / rel
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    return target


def find_workspace_root(start: Path) -> Optional[Path]:
    """Walk up from start until we find a directory containing the workspace marker."""
    start = Path(start).resolve()
    if not start.exists():
        start = start.parent
    for candidate in [start, *start.parents]:
        if (candidate / WORKSPACE_MARKER).is_file() and (candidate / "wiki").is_dir():
            return candidate
    return None


@dataclass(frozen=True)
class WorkspaceLayout:
    root: Path

    @property
    def raw_pdf(self) -> Path: return self.root / "raw" / "pdf"

    @property
    def raw_markdown(self) -> Path: return self.root / "raw" / "markdown"

    @property
    def manifests(self) -> Path: return self.root / "raw" / "manifests"

    @property
    def wiki(self) -> Path: return self.root / "wiki"

    @property
    def wiki_sources(self) -> Path: return self.wiki / "sources"

    @property
    def wiki_concepts(self) -> Path: return self.wiki / "concepts"

    @property
    def wiki_entities(self) -> Path: return self.wiki / "entities"

    @property
    def wiki_index(self) -> Path: return self.wiki / "index.md"

    @property
    def wiki_log(self) -> Path: return self.wiki / "log.md"

    @property
    def ledger(self) -> Path: return self.root / "claims" / "ledger.jsonl"

    @property
    def conflicts(self) -> Path: return self.root / "claims" / "conflicts.jsonl"

    @property
    def dataset(self) -> Path: return self.root / "graph" / "dataset.trig"

    @property
    def shapes(self) -> Path: return self.root / "graph" / "shapes.ttl"

    @property
    def graph_reports(self) -> Path: return self.root / "graph" / "reports"


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.workspace",
        description="Manage a book workspace.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a new workspace at TARGET.")
    init.add_argument("target", type=Path, help="Path to the new workspace.")
    args = parser.parse_args(argv)
    if args.command == "init":
        root = init_workspace(args.target)
        print(f"initialized workspace at {root}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
