"""Heuristic OntoClean-style review of the workspace taxonomy.

Detects role-as-subclass-of-identity-class mistakes:
 - Role classes (named *Editor, *Reviewer, *Author, *Reader, *Manager, *Curator, *Maintainer)
   declared as rdfs:subClassOf an identity-bearing class (Person, Agent, User).
"""
from __future__ import annotations

import sys
from pathlib import Path

from rdflib import Dataset, Graph, RDFS

from .workspace import WorkspaceLayout

ROLE_SUFFIXES = ("Editor", "Reviewer", "Author", "Reader", "Manager", "Maintainer", "Curator")
IDENTITY_CLASS_HINTS = ("Person", "Agent", "User")


def _load_data_graph(layout: WorkspaceLayout) -> Graph:
    """Load workspace data — try TriG first (named graphs), fall back to Turtle."""
    if not layout.dataset.exists() or layout.dataset.stat().st_size == 0:
        return Graph()
    text = layout.dataset.read_text(encoding="utf-8")
    if "{" in text:
        ds = Dataset(default_union=True)
        ds.parse(layout.dataset, format="trig")
        return ds
    g = Graph()
    g.parse(layout.dataset, format="turtle")
    return g


def audit_taxonomy(layout: WorkspaceLayout) -> list[dict]:
    g = _load_data_graph(layout)
    findings: list[dict] = []
    for sub, _, sup in g.triples((None, RDFS.subClassOf, None)):
        sub_name = str(sub).rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        sup_name = str(sup).rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        if any(sub_name.endswith(suffix) for suffix in ROLE_SUFFIXES) and \
           any(hint in sup_name for hint in IDENTITY_CLASS_HINTS):
            findings.append({
                "rule": "ontoclean-role-as-subclass",
                "subject": str(sub),
                "object": str(sup),
                "message": f"Role class {sub_name} should not be a subclass of identity-bearing class {sup_name}.",
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: audit_taxonomy.py <workspace-dir>", file=sys.stderr)
        return 2
    layout = WorkspaceLayout(Path(argv[1]))
    findings = audit_taxonomy(layout)
    for f in findings:
        print(f["message"])
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
