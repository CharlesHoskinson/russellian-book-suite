"""Query the workspace graph for evidence available to a chapter."""
from __future__ import annotations

from pathlib import Path

from rdflib import Dataset, Literal

from .sibling_skills import load_book_knowledge_module


_QUERY = """
PREFIX tbf: <https://example.org/book-knowledge#>

SELECT DISTINCT ?claim WHERE {
  ?claim tbf:supportsChapter ?chapter ;
         tbf:status "verified" .
  FILTER (STR(?chapter) = ?target_str)
}
ORDER BY ?claim
"""


def _load_workspace_dataset(workspace: Path):
    workspace_mod = load_book_knowledge_module("workspace")
    layout = workspace_mod.WorkspaceLayout(Path(workspace).resolve())
    ds = Dataset(default_union=True)
    if layout.dataset.exists() and layout.dataset.stat().st_size > 0:
        ds.parse(layout.dataset, format="trig")
    return ds, layout


def _claim_id_from_uri(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def query_chapter_evidence(workspace: Path, chapter_id: str) -> dict:
    ds, _ = _load_workspace_dataset(workspace)
    target_str = f"https://example.org/book-knowledge/chapters/{chapter_id}"
    claims = sorted({
        _claim_id_from_uri(str(row[0]))
        for row in ds.query(_QUERY, initBindings={"target_str": Literal(target_str)})
    })
    return {"chapter_id": chapter_id, "claims": claims}
