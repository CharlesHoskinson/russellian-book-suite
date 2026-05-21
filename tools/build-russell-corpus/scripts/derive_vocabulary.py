"""Derive a controlled-vocabulary tag set from the existing russellian-style index.

Each unique tag string in any paragraph's `tags` array becomes one controlled-vocabulary
entry. The entry carries the slug, the paragraph IDs that anchor it, and a placeholder
prose definition the operator fills in during one-time review before the first extraction
batch runs.

This script runs ONCE before the first extraction batch. The output `vocabulary.json` is
committed and treated as stable; new tags discovered during extraction route through
`proposed-tags.jsonl` in `sentinel.py` for batched operator review.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.corpus_io import read_index


def derive_controlled_vocabulary(index_path: Path, out_path: Path) -> None:
    """Read existing index, cluster tags, write vocabulary.json."""
    idx = read_index(index_path)
    tag_to_anchors: dict[str, list[str]] = {}
    for entry in idx["paragraphs"]:
        for tag in entry.get("tags", []):
            tag_to_anchors.setdefault(tag, []).append(entry["id"])
    vocab_entries = [
        {
            "slug": slug,
            "definition": "",  # operator fills in during one-time review
            "anchor_ids": sorted(anchors),
        }
        for slug, anchors in sorted(tag_to_anchors.items())
    ]
    out = {
        "version": idx.get("version", "0.1.0"),
        "tag_count": len(vocab_entries),
        "tags": vocab_entries,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    derive_controlled_vocabulary(args.index, args.out)
