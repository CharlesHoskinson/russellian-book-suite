"""Load all chapter contracts and emit a numbered table of contents."""
from __future__ import annotations

from pathlib import Path

from .chapter_contract import load_contract


def build_toc(workspace: Path) -> str:
    contracts_dir = Path(workspace) / "chapters" / "contracts"
    if not contracts_dir.is_dir():
        raise FileNotFoundError(f"no contracts dir at {contracts_dir}")
    contracts = []
    for path in sorted(contracts_dir.glob("ch-*.yaml")):
        c = load_contract(path)
        n = int(c["chapter_id"].split("-")[1])
        contracts.append((n, c["chapter_id"], c["title"]))
    contracts.sort(key=lambda x: x[0])
    lines = ["# Table of Contents", ""]
    for n, cid, title in contracts:
        lines.append(f"{n}. **{title}** (`{cid}`)")
    return "\n".join(lines)


def lookup_chapter(workspace: Path, chapter_id: str) -> tuple[int, str]:
    contracts_dir = Path(workspace) / "chapters" / "contracts"
    contract = load_contract(contracts_dir / f"{chapter_id}.yaml")
    n = int(contract["chapter_id"].split("-")[1])
    return n, contract["title"]
