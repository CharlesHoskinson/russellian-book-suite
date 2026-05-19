"""REQ-RETRIEVAL-043: build a semantic index from work/claims.edn.

Reads the active claims.edn, embeds each atom's :doc field with the
configured sentence-transformers encoder, and writes the index to
work/semantic-index.npz. Skips re-embedding when the claims.edn
SHA-256 matches the SHA stored in the existing .npz (cache reuse).

Graceful degradation: if sentence-transformers is unavailable or the
model cannot be loaded, this script emits a warning and exits 0 so the
rest of the build continues. The verdict's :semantic-neighbours field
will be empty.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from scripts._edn_reader import Keyword, read_edn
from scripts._semantic_index import (
    EmbeddingUnavailableError,
    SemanticIndex,
)

_KW_ATOMS = Keyword("atoms")
_KW_ID = Keyword("id")
_KW_DOC = Keyword("doc")
_KW_KIND = Keyword("kind")


def _iter_doc_atoms(payload: dict) -> Iterable[tuple[str, str]]:
    """Yield (claim_id, doc_text) for each atom carrying both fields.

    Atoms without :doc (e.g. context symbols) are skipped.
    """
    atoms: Any = payload.get(_KW_ATOMS, []) or []
    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        cid = atom.get(_KW_ID)
        doc = atom.get(_KW_DOC)
        if not cid or not doc:
            continue
        yield str(cid), str(doc)


def run(claims_edn: Path, out_path: Path) -> int:
    """Build the index. Returns exit code (always 0 — graceful degrade)."""
    if not claims_edn.exists():
        print(
            f"[build_semantic_index] no {claims_edn}; nothing to embed",
            file=sys.stderr,
        )
        return 0
    if os.environ.get("NEUROSYM_EMBED_DISABLE") == "1":
        print(
            "[build_semantic_index] NEUROSYM_EMBED_DISABLE=1; skipping",
            file=sys.stderr,
        )
        return 0

    claims_text = claims_edn.read_text(encoding="utf-8")
    payload = read_edn(claims_text)

    idx = SemanticIndex(cache_path=out_path)
    # Reuse existing embeddings when SHA-256 matches.
    idx.load()
    pre_sha = idx.claims_sha
    idx.invalidate_if_claims_changed(claims_text)
    if pre_sha and pre_sha == idx.claims_sha and idx.count() > 0:
        print(
            f"[build_semantic_index] cache hit "
            f"(sha={idx.claims_sha[:12]}, n={idx.count()}); skipping embed",
            file=sys.stderr,
        )
        return 0

    pairs = list(_iter_doc_atoms(payload))
    if not pairs:
        print(
            "[build_semantic_index] no atoms with :doc field; "
            "writing empty index",
            file=sys.stderr,
        )
        idx.save()
        return 0

    try:
        for cid, doc in pairs:
            idx.embed_claim(claim_id=cid, text=doc)
    except EmbeddingUnavailableError as e:
        print(
            f"[build_semantic_index] embedding unavailable: {e}",
            file=sys.stderr,
        )
        print(
            "[build_semantic_index] continuing without semantic index "
            "(verdict :semantic-neighbours will be empty)",
            file=sys.stderr,
        )
        return 0

    idx.save()
    print(
        f"[build_semantic_index] wrote {out_path} "
        f"(n={idx.count()}, sha={idx.claims_sha[:12]})",
        file=sys.stderr,
    )
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--claims",
        default="work/claims.edn",
        help="path to claims.edn (default: work/claims.edn)",
    )
    ap.add_argument(
        "--out",
        default="work/semantic-index.npz",
        help="path to semantic-index.npz (default: work/semantic-index.npz)",
    )
    args = ap.parse_args(argv)
    return run(Path(args.claims), Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
