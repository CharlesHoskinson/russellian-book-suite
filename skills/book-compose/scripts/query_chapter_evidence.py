"""Query the workspace graph for evidence available to a chapter (P5.1, REQ-KG-019).

Cutover: the verified claims supporting a chapter are read from book-knowledge's
Cozo store — the relational projection of the claim LEDGER (project_ledger_cozo) —
NOT by parsing the TriG dataset. The booklogic defquery joins the ``claim-chapter``
coverage edge (the relational form of project_graph's ``tbf:supportsChapter``) with
the claim's ``status``, reproducing the old SPARQL ``?claim tbf:supportsChapter
?chapter ; tbf:status "verified"``. book-knowledge's modules are reached through
the repo-sibling-first ``sibling_skills`` bridge.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from .sibling_skills import book_knowledge_root, load_book_knowledge_module

# Mirrors project_ledger_cozo._chapter_uri / project_graph's chapter-URI minting
# (base + urllib.quote(id), default safe="/") so the literal we match equals the
# value stored in the claim-chapter.chapter column for ANY chapter id — not just
# URL-safe slugs. Using quote() also makes the EDN string literal injection-safe
# (a stray '"' in the id is percent-encoded).
_CHAPTER_BASE = "https://example.org/book-knowledge/chapters/"


def _chapter_evidence_edn(chapter_uri: str) -> str:
    """A booklogic defquery: verified claims that support ``chapter_uri``.

    The chapter URI is a controlled value (our own minted prefix + the chapter id),
    embedded as a string literal in the :where clause.
    """
    return (
        "(defquery :chapter-evidence "
        ":find [?claim-id] "
        ":where [[?cc :claim-chapter/claim-id ?claim-id] "
        f'[?cc :claim-chapter/chapter "{chapter_uri}"] '
        "[?c :claim/id ?claim-id] "
        '[?c :claim/status "verified"]])'
    )


def query_chapter_evidence(workspace: Path, chapter_id: str) -> dict:
    cozo_store = load_book_knowledge_module("cozo_store")
    project_ledger_cozo = load_book_knowledge_module("project_ledger_cozo")
    workspace_mod = load_book_knowledge_module("workspace")

    layout = workspace_mod.WorkspaceLayout(Path(workspace).resolve())
    schema = book_knowledge_root() / "assets" / "kg-schema.edn"
    store = cozo_store.CozoStore.in_memory(schema_path=schema)
    project_ledger_cozo.project_ledger(layout, store)

    chapter_uri = f"{_CHAPTER_BASE}{quote(chapter_id)}"
    rows = store.query_edn(_chapter_evidence_edn(chapter_uri))
    claims = sorted({row[0] for row in rows})
    return {"chapter_id": chapter_id, "claims": claims}
