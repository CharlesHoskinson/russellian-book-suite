"""Stage-2 thesis-spine linter: paragraph back-pointers vs the thesis tree.

Walks every paragraph in the assembled manuscript and joins each one against
the compiled thesis triples produced by ``compile_thesis.py``. Emits D9 / D12
defect tickets for the ``book-qa`` gate.

Defect kinds:
  D9  no-support        paragraph carries no `supports:` declaration
  D9  broken-supports   `supports:` names a node not present in the tree
  D9  unreachable       `supports:` node does not transitively reach :Thesis
  D12 unadvanced        sub-argument node has no paragraph naming it

Usage: ``python lint_supports.py <workspace> <release-version>``
Reads <workspace>/.knowledge/thesis-triples.ttl and
<workspace>/book/releases/<version>/manuscript.md, writes
<workspace>/qa/supports-defects.json. Exits 1 if any orphan found.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

NS = Namespace("https://russellian.book/thesis/")


@dataclass
class Defect:
    class_: str   # "D9" or "D12"
    kind: str
    where: str
    detail: str


def _local(uri: URIRef) -> str:
    s = str(uri)
    if s.startswith(str(NS)):
        return s[len(str(NS)):]
    # Fallback: take the bit after the last / or #
    return re.split(r"[#/]", s)[-1]


def load_thesis_tree(ttl_path: Path) -> tuple[set[str], dict[str, set[str]]]:
    """Return (node_ids, supports_edges) where edges map child -> {parents}.

    Nodes considered part of the tree are those typed ``:ThesisNode`` or
    ``:SubArgument``. Invariants and evidence-source IRIs are skipped.
    """
    g = Graph()
    g.parse(ttl_path, format="turtle")
    tree_types = {NS["ThesisNode"], NS["SubArgument"]}
    nodes: set[str] = set()
    for s, _p, o in g.triples((None, RDF.type, None)):
        if isinstance(s, URIRef) and o in tree_types:
            nodes.add(_local(s))
    edges: dict[str, set[str]] = {}
    for s, _p, o in g.triples((None, NS["supports"], None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            child, parent = _local(s), _local(o)
            if child in nodes and parent in nodes:
                edges.setdefault(child, set()).add(parent)
    return nodes, edges


def reaches_thesis(node: str, edges: dict[str, set[str]]) -> bool:
    """Transitive closure: does `node` reach :Thesis via :supports edges?"""
    if node == "Thesis":
        return True
    seen: set[str] = set()
    stack = [node]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        if cur == "Thesis":
            return True
        for parent in edges.get(cur, ()):
            if parent not in seen:
                stack.append(parent)
    return False


# ------------------------------------------------------------ paragraph scan

FENCED_DIV_RE = re.compile(
    r'^:::\s*paragraph\s+([^\n]*?)\n(?P<body>.*?)\n:::\s*$',
    re.DOTALL | re.MULTILINE,
)
COMMENT_RE = re.compile(
    r'^\s*<!--\s*supports:\s*(?P<node>[^;\s]+)\s*(?:;\s*evidence:[^>]*)?-->'
)
ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
CHAPTER_RE = re.compile(r'^# Chapter\s+(\d+)', re.MULTILINE)


@dataclass
class ParaRef:
    chapter: int
    line: int
    supports: str | None
    raw: str


def _chapter_at(md: str, offset: int) -> int:
    n = 0
    for m in CHAPTER_RE.finditer(md):
        if m.start() > offset:
            break
        n = int(m.group(1))
    return n


def scan_paragraphs(md: str) -> list[ParaRef]:
    """Locate paragraph blocks and pull `supports` from either carrier syntax.

    (a) pandoc fenced div: ::: paragraph supports="<id>" evidence="<clm>"
    (b) HTML comment heading a normal paragraph:
        <!-- supports: <id>; evidence: clm-... -->
    Paragraphs without either are reported as no-support.
    """
    out: list[ParaRef] = []
    consumed: list[tuple[int, int]] = []
    for m in FENCED_DIV_RE.finditer(md):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        out.append(ParaRef(
            chapter=_chapter_at(md, m.start()),
            line=md.count("\n", 0, m.start()) + 1,
            supports=attrs.get("supports") or None,
            raw=m.group("body").strip()[:80],
        ))
        consumed.append((m.start(), m.end()))

    cursor = 0
    for block in re.split(r"\n\s*\n", md):
        start = md.find(block, cursor)
        cursor = start + len(block) if start >= 0 else cursor
        if start < 0 or any(s <= start < e for s, e in consumed):
            continue
        stripped = block.strip()
        if not stripped or stripped.startswith(("#", "|", "<", ">", "```", ":::", "---", "[^")):
            # An HTML-comment supports carrier begins with "<!--", so it lands
            # in this branch too. Keep it only when COMMENT_RE matches; every
            # other "<"-prefixed (or markup) block is skipped.
            if not COMMENT_RE.match(stripped):
                continue
        cm = COMMENT_RE.match(stripped)
        out.append(ParaRef(
            chapter=_chapter_at(md, start),
            line=md.count("\n", 0, start) + 1,
            supports=cm.group("node") if cm else None,
            raw=stripped[:80],
        ))
    return out


# ------------------------------------------------------------------ analysis

def analyse(paragraphs: list[ParaRef], nodes: set[str],
            edges: dict[str, set[str]]) -> tuple[list[Defect], dict]:
    defects: list[Defect] = []
    cited: set[str] = set()
    n_supported = n_no = n_broken = n_unreach = 0
    # 3.7: supports tracking is opt-in per manuscript. A document that declares
    # NO carriers (e.g. a freshly assembled manuscript whose paragraphs were
    # never annotated) is not in tracking mode, so a missing carrier is not an
    # orphan — flagging every paragraph would be noise, not signal. Once ANY
    # paragraph declares a carrier, the carrier-less ones are flagged normally.
    supports_tracking = any(p.supports is not None for p in paragraphs)
    for p in paragraphs:
        loc = f"ch-{p.chapter:02d} line {p.line}" if p.chapter else f"line {p.line}"
        if p.supports is None:
            if supports_tracking:
                defects.append(Defect("D9", "no-support", loc,
                                      f"paragraph has no supports declaration: {p.raw!r}"))
                n_no += 1
            continue
        if p.supports not in nodes:
            defects.append(Defect("D9", "broken-supports", loc,
                                  f"supports={p.supports!r} is not a node in the thesis tree"))
            n_broken += 1
            continue
        if not reaches_thesis(p.supports, edges):
            defects.append(Defect("D9", "unreachable", loc,
                                  f"supports={p.supports!r} does not transitively reach :Thesis"))
            n_unreach += 1
            continue
        cited.add(p.supports)
        n_supported += 1

    # Only audit sub-argument coverage when the manuscript is in supports-tracking
    # mode; with no carriers every sub-argument would trivially be "unadvanced".
    sub_args = {n for n in nodes if n != "Thesis"}
    unadvanced = sorted(sub_args - cited) if supports_tracking else []
    for sa in unadvanced:
        defects.append(Defect("D12", "unadvanced", sa,
                              f"sub-argument {sa!r} is named by no paragraph's supports"))

    summary = {
        "total_paragraphs": len(paragraphs),
        "supported": n_supported,
        "orphan_no_support": n_no,
        "orphan_broken_supports": n_broken,
        "orphan_unreachable": n_unreach,
        "unadvanced_sub_arguments": unadvanced,
        "supports_tracking": supports_tracking,
    }
    return defects, summary


def _render(d: Defect) -> dict:
    out = asdict(d)
    out["class"] = out.pop("class_")
    return out


def lint(workspace: Path, version: str) -> tuple[list[Defect], dict]:
    ttl = workspace / ".knowledge" / "thesis-triples.ttl"
    md_path = workspace / "book" / "releases" / version / "manuscript.md"
    if not ttl.exists():
        raise FileNotFoundError(ttl)
    if not md_path.exists():
        raise FileNotFoundError(md_path)
    nodes, edges = load_thesis_tree(ttl)
    paragraphs = scan_paragraphs(md_path.read_text(encoding="utf-8"))
    return analyse(paragraphs, nodes, edges)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: lint_supports.py <workspace> <release-version>", file=sys.stderr)
        return 2
    workspace = Path(argv[1]).resolve()
    version = argv[2]
    defects, summary = lint(workspace, version)
    out_dir = workspace / "qa"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "supports-defects.json"
    payload = {"summary": summary, "defects": [_render(d) for d in defects]}
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Linted supports for {workspace.name} @ {version}")
    print(f"  paragraphs: {summary['total_paragraphs']} "
          f"(supported {summary['supported']}, "
          f"no-support {summary['orphan_no_support']}, "
          f"broken {summary['orphan_broken_supports']}, "
          f"unreachable {summary['orphan_unreachable']})")
    print(f"  unadvanced sub-arguments: {len(summary['unadvanced_sub_arguments'])}")
    print(f"  full report: {out_path}")
    n_orphan = (summary["orphan_no_support"]
                + summary["orphan_broken_supports"]
                + summary["orphan_unreachable"])
    return 1 if n_orphan else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
