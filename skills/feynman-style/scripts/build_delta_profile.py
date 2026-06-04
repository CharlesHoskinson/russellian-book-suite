"""Build an OFFLINE word-frequency profile from copies the user owns.

Reads skills/feynman-style/corpus-raw/ (PDF/txt/md), writes
assets/feynman-delta-profile.json. With no drop files, returns None and leaves
the committed thresholds untouched. Never touches the network.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

from scripts.pdf_extract import extract_any

_SKILL_ROOT = Path(__file__).resolve().parent.parent
_DROP = _SKILL_ROOT / "corpus-raw"
_OUT = _SKILL_ROOT / "assets" / "feynman-delta-profile.json"
_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def build_profile_from_texts(texts: list[str], top_n: int = 500) -> dict:
    counts: Counter[str] = Counter()
    for t in texts:
        counts.update(_WORD.findall(t.lower()))
    common = counts.most_common(top_n)
    subtotal = sum(c for _, c in common)
    if subtotal == 0:
        return {}
    return {w: c / subtotal for w, c in common}


def build_profile(corpus_dir: Path = _DROP, out_path: Path = _OUT,
                  top_n: int = 500) -> Optional[Path]:
    if not corpus_dir.exists():
        return None
    sources = [p for p in corpus_dir.iterdir()
               if p.suffix.lower() in (".pdf", ".txt", ".md")]
    if not sources:
        return None
    texts = [extract_any(p) for p in sources]
    profile = build_profile_from_texts(texts, top_n=top_n)
    if not profile:
        return None
    payload = {
        "version": "0.1.0",
        "source_file_count": len(sources),
        "token_basis": "relative_frequency",
        "frequencies": profile,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def main(argv: list[str]) -> int:
    result = build_profile()
    if result is None:
        print("No corpus-raw/ drop files found; using committed thresholds.", file=sys.stderr)
        return 0
    print(f"Wrote profile from local drop -> {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
