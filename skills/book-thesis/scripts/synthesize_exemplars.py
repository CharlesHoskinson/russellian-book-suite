"""Symbolic->LLM exemplar pack generator for the drafting agent.

Reads ``<workspace>/.knowledge/thesis-triples.ttl`` and the claim ledger
(``.knowledge/claims.jsonl``, falling back to ``.knowledge/ledger.jsonl``
then ``claims/ledger.jsonl``) and writes a few-shot bundle to
``<workspace>/.exemplars/<chapter-id>.json``. Each exemplar is a synthetic
(supports-node, claim, paragraph) tuple in Russellian style.

Usage:
    python synthesize_exemplars.py <workspace> <chapter-id>
"""
from __future__ import annotations

import json
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

NS = Namespace("https://russellian.book/thesis/")
THESIS_NODE = URIRef(NS["Thesis"])
SYNTHETIC_TAG = "[SYNTHETIC]"
TARGET_LO, TARGET_HI = 8, 12
HOUSE_STYLE_NOTES = (
    "Russellian style: active voice, declarative, atomic. No hedges. "
    "Cite the claim in square brackets. Two to three sentences per "
    "paragraph. Each paragraph advances exactly one supports-node."
)


@dataclass(frozen=True)
class SubArg:
    node_id: str
    statement: str
    advanced_by: tuple[str, ...]


@dataclass(frozen=True)
class ClaimRec:
    claim_id: str
    canonical_text: str
    chapters: tuple[str, ...]


_SENTENCE_END = re.compile(r"[.!?]\s*$")


def _load_thesis(workspace: Path) -> dict[str, SubArg]:
    ttl = workspace / ".knowledge" / "thesis-triples.ttl"
    if not ttl.exists():
        raise FileNotFoundError(ttl)
    g = Graph()
    g.parse(ttl, format="turtle")
    subs: dict[str, SubArg] = {}
    for node in g.subjects(RDF.type, NS["SubArgument"]):
        node_id = str(node).removeprefix(str(NS))
        stmt = str(g.value(node, NS["statement"]) or "").strip()
        advanced = tuple(str(o).removeprefix(str(NS))
                         for o in g.objects(node, NS["advancedBy"]))
        subs[node_id] = SubArg(node_id, stmt, advanced)
    return subs


def _ledger_path(workspace: Path) -> Path:
    for c in (workspace / ".knowledge" / "claims.jsonl",
              workspace / ".knowledge" / "ledger.jsonl",
              workspace / "claims" / "ledger.jsonl"):
        if c.exists():
            return c
    raise FileNotFoundError(f"no claim ledger under {workspace}")


def _load_claims(workspace: Path) -> list[ClaimRec]:
    """Parse JSONL ledger; collapse supersession chains to the tip."""
    rows: dict[str, dict[str, Any]] = {}
    superseded: set[str] = set()
    with _ledger_path(workspace).open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            cid = rec.get("claim_id")
            if not cid:
                continue
            rows[cid] = rec
            if old := rec.get("supersedes"):
                superseded.add(old)
    return [
        ClaimRec(
            claim_id=cid,
            canonical_text=str(rec.get("canonical_text") or "").strip(),
            chapters=tuple(rec.get("supports_chapters") or []),
        )
        for cid, rec in rows.items()
        if cid not in superseded and rec.get("status") != "superseded"
    ]


def _synthesize_paragraph(claim: ClaimRec, sub: SubArg) -> str:
    body = (claim.canonical_text or "The claim holds.").strip().rstrip(".!?")
    cited = f"{body} [{claim.claim_id}]."
    raw_tie = (f"This fact advances the sub-argument that "
               f"{sub.statement.rstrip('.')}" if sub.statement
               else f"This fact advances the sub-argument {sub.node_id}")
    tie = raw_tie if _SENTENCE_END.search(raw_tie) else raw_tie + "."
    return f"{SYNTHETIC_TAG} {cited} {tie}"


def _select_sub_args(subs: dict[str, SubArg], chapter_id: str) -> list[SubArg]:
    """Prefer :advancedBy declarations; fall back to all sub-arguments."""
    advancing = [s for s in subs.values() if chapter_id in s.advanced_by]
    return advancing or sorted(subs.values(), key=lambda s: s.node_id)


def _select_claims(claims: list[ClaimRec], chapter_id: str,
                   rng: random.Random) -> list[ClaimRec]:
    scoped = [c for c in claims if chapter_id in c.chapters and c.canonical_text]
    if len(scoped) < TARGET_LO:
        extras = [c for c in claims if c not in scoped and c.canonical_text]
        rng.shuffle(extras)
        scoped += extras
    return scoped


def _exemplar(sub: SubArg, claim: ClaimRec) -> dict[str, Any]:
    return {
        "supports_node": sub.node_id,
        "supports_statement": sub.statement,
        "claim_id": claim.claim_id,
        "claim_statement": claim.canonical_text,
        "exemplar_paragraph": _synthesize_paragraph(claim, sub),
        "synthetic": True,
    }


def build_pack(workspace: Path, chapter_id: str) -> dict[str, Any]:
    subs = _load_thesis(workspace)
    if not subs:
        raise ValueError("thesis tree contains no sub-arguments")
    claims = _load_claims(workspace)
    if not claims:
        raise ValueError("claim ledger contains no usable claims")
    rng = random.Random(f"exemplars::{chapter_id}")
    advancing = _select_sub_args(subs, chapter_id)
    pool = _select_claims(claims, chapter_id, rng)
    exemplars: list[dict[str, Any]] = []
    for i, claim in enumerate(pool):
        if len(exemplars) >= TARGET_HI:
            break
        exemplars.append(_exemplar(advancing[i % len(advancing)], claim))
    j = 0
    while len(exemplars) < TARGET_LO and pool:
        exemplars.append(_exemplar(
            advancing[(len(exemplars) + j) % len(advancing)],
            pool[j % len(pool)],
        ))
        j += 1
    return {
        "chapter_id": chapter_id,
        "advances_sub_arguments": [s.node_id for s in advancing],
        "exemplars": exemplars[:TARGET_HI],
        "house_style_notes": HOUSE_STYLE_NOTES,
    }


def synthesize_exemplars(workspace: Path, chapter_id: str) -> Path:
    pack = build_pack(workspace, chapter_id)
    out_dir = workspace / ".exemplars"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{chapter_id}.json"
    out_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    return out_path


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: synthesize_exemplars.py <workspace> <chapter-id>",
              file=sys.stderr)
        return 2
    workspace = Path(argv[1]).resolve()
    chapter_id = argv[2]
    try:
        out_path = synthesize_exemplars(workspace, chapter_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    pack = json.loads(out_path.read_text(encoding="utf-8"))
    print(f"wrote {len(pack['exemplars'])} exemplars to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
