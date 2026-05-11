"""Compile a thesis YAML into RDF triples for the book-knowledge graph.

Reads ``<workspace>/thesis/<book-id>.yaml`` (schema in ``thesis/schema.yaml``)
and emits Turtle to ``<workspace>/.knowledge/thesis-triples.ttl``.

Triple shape:

    @prefix : <https://russellian.book/thesis/> .

    :Thesis a :ThesisNode ;
        :statement "..." ;
        :polarity "descriptive" ;
        :scope "..." .

    :<sub_id> a :SubArgument ;
        :supports :<parent> ;
        :statement "..." ;
        :polarity "..." ;
        :requiresEvidence :<source_id> , :<source_id> .

    :<inv_id> a :Invariant ;
        :rule "..." ;
        :formal "..." .

Idempotent: re-running with identical input produces identical output.

Usage:
    python compile_thesis.py <workspace> <book-id>
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

NS = Namespace("https://russellian.book/thesis/")
THESIS_NODE = URIRef(NS["Thesis"])


@dataclass(frozen=True)
class CompileResult:
    """Summary of a compile pass."""

    book_id: str
    sub_arguments: int
    invariants: int
    output_path: Path


def _slug_uri(slug: str) -> URIRef:
    """Coerce a YAML id into a namespaced URI."""
    return URIRef(NS[slug.strip()])


def _load_spec(workspace: Path, book_id: str) -> dict[str, Any]:
    path = workspace / "thesis" / f"{book_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    if not isinstance(spec, dict):
        raise ValueError(f"{path}: expected mapping at top level")
    if spec.get("book_id") and spec["book_id"] != book_id:
        raise ValueError(
            f"{path}: book_id {spec['book_id']!r} does not match argument {book_id!r}"
        )
    return spec


def _add_thesis(graph: Graph, thesis: dict[str, Any]) -> None:
    graph.add((THESIS_NODE, RDF.type, NS["ThesisNode"]))
    statement = (thesis.get("statement") or "").strip()
    graph.add((THESIS_NODE, NS["statement"], Literal(statement)))
    if thesis.get("polarity"):
        graph.add((THESIS_NODE, NS["polarity"], Literal(thesis["polarity"].strip())))
    if thesis.get("scope"):
        graph.add((THESIS_NODE, NS["scope"], Literal(thesis["scope"].strip())))


def _add_sub_argument(graph: Graph, sub: dict[str, Any]) -> None:
    if "id" not in sub:
        raise ValueError(f"sub_argument missing id: {sub!r}")
    node = _slug_uri(sub["id"])
    graph.add((node, RDF.type, NS["SubArgument"]))
    parent_id = (sub.get("parent") or "thesis").strip()
    parent_node = THESIS_NODE if parent_id.lower() == "thesis" else _slug_uri(parent_id)
    graph.add((node, NS["supports"], parent_node))
    if sub.get("statement"):
        graph.add((node, NS["statement"], Literal(sub["statement"].strip())))
    if sub.get("polarity"):
        graph.add((node, NS["polarity"], Literal(sub["polarity"].strip())))
    for ev in sub.get("required_evidence") or []:
        graph.add((node, NS["requiresEvidence"], _slug_uri(str(ev))))
    for ch in sub.get("advanced_by_chapters") or []:
        graph.add((node, NS["advancedBy"], _slug_uri(str(ch))))


def _add_invariant(graph: Graph, inv: dict[str, Any]) -> None:
    if "id" not in inv:
        raise ValueError(f"invariant missing id: {inv!r}")
    node = _slug_uri(inv["id"])
    graph.add((node, RDF.type, NS["Invariant"]))
    if inv.get("rule"):
        graph.add((node, NS["rule"], Literal(inv["rule"].strip())))
    if inv.get("formal"):
        graph.add((node, NS["formal"], Literal(inv["formal"].strip())))


def compile_thesis(workspace: Path, book_id: str) -> CompileResult:
    """Compile ``thesis/<book-id>.yaml`` into a Turtle file."""
    spec = _load_spec(workspace, book_id)
    graph = Graph()
    graph.bind("", NS)

    _add_thesis(graph, spec.get("thesis") or {})

    subs = spec.get("sub_arguments") or []
    for sub in subs:
        _add_sub_argument(graph, sub)

    invs = spec.get("invariants") or []
    for inv in invs:
        _add_invariant(graph, inv)

    out_dir = workspace / ".knowledge"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "thesis-triples.ttl"
    # sort=True + identical input -> identical output (idempotent).
    data = graph.serialize(format="turtle", encoding="utf-8", sort=True)
    out_path.write_bytes(data)

    return CompileResult(
        book_id=book_id,
        sub_arguments=len(subs),
        invariants=len(invs),
        output_path=out_path,
    )


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: compile_thesis.py <workspace> <book-id>", file=sys.stderr)
        return 2
    workspace = Path(argv[1]).resolve()
    book_id = argv[2]
    try:
        result = compile_thesis(workspace, book_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"compiled thesis for {result.book_id}")
    print(f"  sub-arguments: {result.sub_arguments}")
    print(f"  invariants:    {result.invariants}")
    print(f"  output:        {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
