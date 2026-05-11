"""Run pyshacl over the workspace dataset against the workspace shapes."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pyshacl
from rdflib import Dataset, Graph

from .workspace import WorkspaceLayout

ASSETS = Path(__file__).resolve().parent.parent / "assets"


@dataclass(frozen=True)
class Violation:
    focus_node: str
    path: str
    message: str


@dataclass(frozen=True)
class ShaclReport:
    conforms: bool
    violations: list[Violation]
    text: str


def _load_data(layout: WorkspaceLayout) -> Graph:
    ds = Dataset(default_union=True)
    if layout.dataset.exists() and layout.dataset.stat().st_size > 0:
        ds.parse(layout.dataset, format="trig")
    return ds


def _load_shapes(layout: WorkspaceLayout) -> Graph:
    g = Graph()
    if layout.shapes.exists() and layout.shapes.stat().st_size > 0:
        g.parse(layout.shapes, format="turtle")
    else:
        g.parse(ASSETS / "shapes.ttl", format="turtle")
    return g


def _parse_violations(report_graph: Graph) -> list[Violation]:
    from rdflib import URIRef
    out: list[Violation] = []
    for result in report_graph.subjects(predicate=URIRef("http://www.w3.org/ns/shacl#focusNode")):
        focus = report_graph.value(result, URIRef("http://www.w3.org/ns/shacl#focusNode"))
        path = report_graph.value(result, URIRef("http://www.w3.org/ns/shacl#resultPath"))
        msg = report_graph.value(result, URIRef("http://www.w3.org/ns/shacl#resultMessage"))
        out.append(Violation(
            focus_node=str(focus) if focus else "",
            path=str(path) if path else "",
            message=str(msg) if msg else "",
        ))
    return out


def validate_shacl(layout: WorkspaceLayout) -> ShaclReport:
    data = _load_data(layout)
    shapes = _load_shapes(layout)

    conforms, report_graph, report_text = pyshacl.validate(
        data_graph=data,
        shacl_graph=shapes,
        inference="rdfs",
        allow_warnings=False,
        meta_shacl=False,
        advanced=True,
    )

    violations = _parse_violations(report_graph) if not conforms else []

    layout.graph_reports.mkdir(parents=True, exist_ok=True)
    (layout.graph_reports / "shacl-latest.txt").write_text(report_text, encoding="utf-8")

    return ShaclReport(conforms=conforms, violations=violations, text=report_text)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_shacl.py <workspace-dir>", file=sys.stderr)
        return 2
    layout = WorkspaceLayout(Path(argv[1]))
    report = validate_shacl(layout)
    print(report.text)
    return 0 if report.conforms else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
