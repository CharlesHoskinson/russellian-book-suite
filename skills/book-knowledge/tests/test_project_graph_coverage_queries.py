"""Tests for C-001: chapter/wiki-page/dateCreated triples emitted by project_graph."""
import json
from pathlib import Path

from rdflib import Dataset, Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF
from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.project_graph import project_graph

TBF = Namespace("https://example.org/book-knowledge#")
SCHEMA = Namespace("https://schema.org/")
BASE = "https://example.org/book-knowledge/"


def _claim(cid: str, chapters=(), ingested_at="2026-05-01T00:00:00Z",
           doc_id="small") -> dict:
    return {
        "claim_id": cid,
        "canonical_text": f"Text for {cid}.",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": doc_id, "locator_text": "some text"}],
        "supports_chapters": list(chapters),
        "created_at": "2026-05-01T00:00:00Z",
    }


# --- C-001a: tbf:Chapter triples ---

def test_chapter_type_triple_emitted(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.ledger.write_text(
        json.dumps(_claim("clm-2026-000001", chapters=["ch-01"])) + "\n",
        encoding="utf-8",
    )
    out = project_graph(layout)
    g = Graph()
    g.parse(out, format="trig")
    ch_uri = URIRef(f"{BASE}chapters/ch-01")
    types = list(g.triples((ch_uri, RDF.type, TBF.Chapter)))
    assert types, "expected (chapter_uri, rdf:type, tbf:Chapter) triple"


def test_chapter_type_not_emitted_when_no_chapters(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.ledger.write_text(
        json.dumps(_claim("clm-2026-000001", chapters=[])) + "\n",
        encoding="utf-8",
    )
    out = project_graph(layout)
    g = Graph()
    g.parse(out, format="trig")
    chapters = list(g.triples((None, RDF.type, TBF.Chapter)))
    assert chapters == []


# --- C-001b: tbf:WikiPage triples ---

def test_wiki_page_type_triple_emitted(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.ledger.write_text(
        json.dumps(_claim("clm-2026-000001")) + "\n",
        encoding="utf-8",
    )
    # create a wiki page
    wiki_file = layout.wiki / "sources" / "some-topic.md"
    wiki_file.parent.mkdir(parents=True, exist_ok=True)
    wiki_file.write_text("# Some Topic\n", encoding="utf-8")

    out = project_graph(layout)
    g = Graph()
    g.parse(out, format="trig")
    pages = list(g.triples((None, RDF.type, TBF.WikiPage)))
    assert pages, "expected (page_uri, rdf:type, tbf:WikiPage) triple for each wiki md file"


def test_wiki_page_uri_uses_relative_path(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.ledger.write_text(
        json.dumps(_claim("clm-2026-000001")) + "\n",
        encoding="utf-8",
    )
    wiki_file = layout.wiki / "concepts" / "economics.md"
    wiki_file.parent.mkdir(parents=True, exist_ok=True)
    wiki_file.write_text("# Economics\n", encoding="utf-8")

    out = project_graph(layout)
    g = Graph()
    g.parse(out, format="trig")
    pages = [str(s) for s, p, o in g.triples((None, RDF.type, TBF.WikiPage))]
    assert any("economics" in p for p in pages)


# --- C-001c: schema:dateCreated on source URIs from manifests ---

def test_source_date_created_emitted(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.ledger.write_text(
        json.dumps(_claim("clm-2026-000001", doc_id="small")) + "\n",
        encoding="utf-8",
    )
    manifest = layout.manifests / "small.json"
    manifest.write_text(json.dumps({
        "doc_name": "small",
        "doc_id": "small",
        "source_kind": "markdown",
        "sha256": "a" * 64,
        "ingested_at": "2026-04-01T12:00:00Z",
        "node_count": 5,
    }), encoding="utf-8")

    out = project_graph(layout)
    g = Graph()
    g.parse(out, format="trig")
    dates = list(g.triples((None, SCHEMA.dateCreated, None)))
    # At least one dateCreated triple (the source's ingested_at)
    assert dates, "expected at least one schema:dateCreated triple from manifest ingested_at"


def test_source_date_created_value_matches_ingested_at(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    layout.ledger.write_text(
        json.dumps(_claim("clm-2026-000001", doc_id="mybook")) + "\n",
        encoding="utf-8",
    )
    manifest = layout.manifests / "mybook.json"
    manifest.write_text(json.dumps({
        "doc_name": "mybook",
        "doc_id": "mybook",
        "source_kind": "pdf",
        "sha256": "b" * 64,
        "ingested_at": "2026-03-15T08:30:00Z",
        "node_count": 12,
    }), encoding="utf-8")

    out = project_graph(layout)
    g = Graph()
    g.parse(out, format="trig")
    dates = [str(o) for s, p, o in g.triples((None, SCHEMA.dateCreated, None))]
    assert any("2026-03-15" in d for d in dates), f"expected ingested_at date in triples, got {dates}"
