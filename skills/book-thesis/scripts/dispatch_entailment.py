"""Stage-3 per-paragraph entailment dispatch preparer.

For every manuscript paragraph that declares a valid ``supports:`` node,
write a small JSON payload to ``<workspace>/qa/entailment-payloads/``.
Each payload feeds a fresh-context LLM critic that returns ``entailed |
weakly-entailed | unrelated | contradicts``. Does not spawn agents.

Usage: ``python dispatch_entailment.py <workspace> <release-version>``
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, URIRef

THESIS_NS = "https://russellian.book/thesis/"
PARAGRAPH_CHAR_BUDGET = 600
MAX_SIBLINGS = 3
EXPECTED = "entailed | weakly-entailed | unrelated | contradicts"
FENCED_DIV_RE = re.compile(
    r'^:::\s*paragraph\s+([^\n]*?)\n(?P<body>.*?)\n:::\s*$',
    re.DOTALL | re.MULTILINE)
ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
COMMENT_RE = re.compile(
    r'^\s*<!--\s*supports:\s*(?P<node>[^;\s]+)'
    r'(?:\s*;\s*evidence:\s*(?P<ev>[A-Za-z0-9_-]+))?\s*-->')
CHAPTER_RE = re.compile(r'^# Chapter\s+(\d+)', re.MULTILINE)
@dataclass
class ThesisNode:
    """A node in the compiled thesis tree."""
    id: str
    statement: str = ""
    parent: str | None = None
@dataclass
class ParaRef:
    """A manuscript paragraph located in document order."""
    chapter: int
    paragraph_idx: int
    supports: str | None
    evidence: str | None
    text: str
@dataclass
class ParaPayload:
    """The JSON-serialisable entailment-critic payload for one paragraph."""
    paragraph: str
    supports_node: str
    supports_statement: str
    cited_claim: str
    sibling_nodes: list[dict[str, str]] = field(default_factory=list)
    expected_response: str = EXPECTED
    meta: dict[str, Any] = field(default_factory=dict)
def _local(uri: URIRef | str) -> str:
    s = str(uri)
    for sep in ("#", "/"):
        if sep in s:
            s = s.rsplit(sep, 1)[-1]
    return s
def _slug(c: int) -> str:
    return f"ch-{c:02d}" if c else "ch-00"
def _truncate(text: str, budget: int = PARAGRAPH_CHAR_BUDGET) -> str:
    text = " ".join(text.split())
    return text if len(text) <= budget else text[: budget - 1].rstrip() + "…"
def load_thesis_tree(ttl_path: Path) -> dict[str, ThesisNode]:
    """Parse ``thesis-triples.ttl`` into ``{local_name: ThesisNode}``."""
    g = Graph()
    g.parse(ttl_path, format="turtle")
    nodes: dict[str, ThesisNode] = {}
    for s, p, o in g:
        if not isinstance(s, URIRef) or not str(s).startswith(THESIS_NS):
            continue
        node = nodes.setdefault(_local(s), ThesisNode(id=_local(s)))
        pred = _local(p)
        if pred == "statement" and isinstance(o, Literal):
            node.statement = str(o).strip()
        elif pred == "supports" and isinstance(o, URIRef):
            node.parent = _local(o)
            nodes.setdefault(node.parent, ThesisNode(id=node.parent))
    return nodes

def siblings_of(node_id: str, tree: dict[str, ThesisNode]) -> list[ThesisNode]:
    """Return up to ``MAX_SIBLINGS`` nodes that share ``node_id``'s parent."""
    target = tree.get(node_id)
    if target is None or target.parent is None:
        return []
    sibs = sorted(
        (n for nid, n in tree.items()
         if nid != node_id and n.parent == target.parent and n.statement),
        key=lambda n: n.id)
    return sibs[:MAX_SIBLINGS]

def scan_paragraphs(md: str) -> list[ParaRef]:
    """Locate every paragraph carrier (fenced div or HTML-comment) in order."""
    spans: list[tuple[int, str | None, str | None, str]] = []
    consumed: list[tuple[int, int]] = []
    for m in FENCED_DIV_RE.finditer(md):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        spans.append((m.start(), attrs.get("supports") or None,
                      attrs.get("evidence") or None, m.group("body").strip()))
        consumed.append((m.start(), m.end()))
    cursor = 0
    for block in re.split(r"\n\s*\n", md):
        start = md.find(block, cursor)
        if start < 0:
            continue
        cursor = start + len(block)
        stripped = block.strip()
        if any(s <= start < e for s, e in consumed) or not stripped \
                or stripped.startswith(("#", "|", ">", "```", ":::", "---")):
            continue
        cm = COMMENT_RE.match(stripped)
        spans.append((start, cm.group("node") if cm else None,
                      cm.group("ev") if cm else None, stripped))
    spans.sort(key=lambda t: t[0])
    chapters = [(m.start(), int(m.group(1))) for m in CHAPTER_RE.finditer(md)]
    counters: dict[int, int] = {}
    out: list[ParaRef] = []
    for offset, supports, evidence, text in spans:
        chapter = max((n for off, n in chapters if off <= offset), default=0)
        counters[chapter] = counters.get(chapter, 0) + 1
        out.append(ParaRef(chapter, counters[chapter], supports, evidence, text))
    return out

def load_claim_index(ledger_path: Path) -> dict[str, str]:
    """Return ``claim_id -> canonical_text`` from ``claims/ledger.jsonl``."""
    out: dict[str, str] = {}
    if not ledger_path.exists():
        return out
    for raw in ledger_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        cid, text = rec.get("claim_id"), rec.get("canonical_text")
        if isinstance(cid, str) and isinstance(text, str):
            out[cid] = text
    return out

def prepare_payloads(workspace: Path, version: str) -> list[tuple[str, ParaPayload]]:
    """Return ``(filename, payload)`` pairs for every supported paragraph."""
    ttl = workspace / ".knowledge" / "thesis-triples.ttl"
    md_path = workspace / "book" / "releases" / version / "manuscript.md"
    for required in (ttl, md_path):
        if not required.exists():
            raise FileNotFoundError(required)
    tree = load_thesis_tree(ttl)
    claims = load_claim_index(workspace / "claims" / "ledger.jsonl")
    pairs: list[tuple[str, ParaPayload]] = []
    for p in scan_paragraphs(md_path.read_text(encoding="utf-8")):
        if not p.supports or p.supports not in tree:
            continue
        node = tree[p.supports]
        payload = ParaPayload(
            paragraph=_truncate(p.text),
            supports_node=node.id,
            supports_statement=node.statement,
            cited_claim=claims.get(p.evidence or "", "") if p.evidence else "",
            sibling_nodes=[{"id": s.id, "statement": s.statement}
                           for s in siblings_of(p.supports, tree)],
            meta={"chapter": _slug(p.chapter),
                  "paragraph_idx": p.paragraph_idx,
                  "evidence_id": p.evidence or ""})
        pairs.append((f"{_slug(p.chapter)}-p{p.paragraph_idx:03d}.json", payload))
    return pairs

def write_payloads(workspace: Path, version: str) -> int:
    """Serialise payloads + ``_index.json``; return the count."""
    pairs = prepare_payloads(workspace, version)
    out_dir = workspace / "qa" / "entailment-payloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for name, payload in pairs:
        (out_dir / name).write_text(
            json.dumps(asdict(payload), indent=2, sort_keys=True), encoding="utf-8")
        index.append({"file": name, "supports_node": payload.supports_node})
    index.sort(key=lambda r: r["file"])
    (out_dir / "_index.json").write_text(
        json.dumps({"version": version, "payloads": index}, indent=2), encoding="utf-8")
    return len(pairs)

def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: dispatch_entailment.py <workspace> <release-version>", file=sys.stderr)
        return 2
    try:
        n = write_payloads(Path(argv[1]).resolve(), argv[2])
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {n} payloads")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
