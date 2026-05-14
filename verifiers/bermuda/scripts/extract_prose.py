"""Walk chapter drafts and extract Pass A prose facts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.prose_patterns import extract_pass_a


def extract_chapter(draft_path: Path) -> list[dict]:
    text = draft_path.read_text(encoding="utf-8")
    return extract_pass_a(text, source_file=str(draft_path.name))


def extract_release(bundles_dir: Path, out_path: Path) -> int:
    """Walk chapter-bundles/*/draft.md and emit all prose-fact atoms."""
    all_atoms: list[dict] = []
    for ch_dir in sorted(bundles_dir.iterdir()):
        if not ch_dir.is_dir():
            continue
        draft = ch_dir / "draft.md"
        if not draft.exists():
            continue
        text = draft.read_text(encoding="utf-8")
        atoms = extract_pass_a(text, source_file=f"{ch_dir.name}/draft.md")
        all_atoms.extend(atoms)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"version": 1, "atoms": all_atoms}, indent=2, sort_keys=True),
        encoding="utf-8", newline="\n",
    )
    return len(all_atoms)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundles", required=True,
                    help="Path to chapter-bundles/ (one dir per chapter, each with draft.md)")
    ap.add_argument("--out", default="work/prose-facts.edn")
    args = ap.parse_args(argv)
    n = extract_release(Path(args.bundles), Path(args.out))
    print(f"extracted {n} prose atoms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
