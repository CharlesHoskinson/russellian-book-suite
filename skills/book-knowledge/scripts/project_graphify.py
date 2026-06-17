"""Project a graphify ``graph.json`` into the Cozo store (P4.1).

`project_graphify(path, store)` reads a graphify code-graph document and loads
its ``nodes`` into the ``code-node`` relation and its ``links`` into the
``code-edge`` relation. This is the code-graph counterpart of
:mod:`project_ledger_cozo` (which projects the claim ledger): both populate the
SAME homoiconic Cozo store, which is what lets a single query span the code graph
and the claims graph together (the headline ability, exercised by
``tests/test_kg_capability.py``).

graphify graph.json shape (mirrors the real
``graphify-out/graph.json``): a top-level map with ``nodes`` and ``links`` lists
(plus ``hyperedges``/token-count metadata this loader ignores).

  - each node: ``{id, label, file_type, source_file, source_location, _origin}``
  - each link: ``{source, target, relation, confidence, weight, ...}``

Field mapping (graphify -> schema column):
  - node ``id`` -> ``code-node/id`` (identity), node ``label`` -> ``code-node/label``.
    ``rank`` and ``community`` are left null; an in-engine recompute pass (P4.2,
    Cozo PageRank + Louvain) is what fills them — graphify's graph.json carries
    no precomputed rank/community of its own.
  - link ``source`` -> ``code-edge/source-id``, link ``target`` ->
    ``code-edge/target-id``, link ``relation`` -> ``code-edge/relationship``,
    link ``weight`` -> ``code-edge/weight`` (typed Float). ``code-edge/id`` (the
    identity column) is minted as a stable hash of the (source, target,
    relationship) triple — see :func:`_edge_id`.

The code-edge identity column is the SYNTHETIC ``id`` = a stable hash of
``(source, target, relationship)``. graphify is a multigraph (a node has many
outgoing links), so keying on ``source-id`` alone would collapse them; the triple
id keeps each distinct edge while upserting cleanly on re-projection.
Determinism: rows are emitted in graph.json order.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def _edge_id(source: str, target: str, relationship: str) -> str:
    """Deterministic, stable id for a code edge.

    graphify links have no id; we mint one from the (source, target,
    relationship) triple so re-projection upserts the same row and so two edges
    sharing a source (a multigraph) stay distinct rows.
    """
    digest = hashlib.sha1(
        "\x1f".join((source, target, relationship)).encode("utf-8")
    ).hexdigest()[:16]
    return f"edge-{digest}"


def project_graphify(path: Path, store) -> None:
    """Load a graphify ``graph.json`` into the store's code-node/code-edge.

    Reads the document at ``path`` (never writes it), maps each node to a
    ``code-node`` row (``id``, ``label``; ``rank``/``community`` left null) and
    each link to a ``code-edge`` row (``source-id``, ``target-id``,
    ``relationship`` from ``relation``, ``weight``). Deterministic: rows follow
    graph.json order. Re-projection upserts (Cozo ``:put`` keys on the identity
    columns) rather than duplicating.
    """
    doc = json.loads(Path(path).read_text(encoding="utf-8"))

    node_rows: list[dict] = []
    for node in doc.get("nodes", []):
        row: dict = {"id": node["id"]}
        if "label" in node:
            row["label"] = node["label"]
        node_rows.append(row)

    edge_rows: list[dict] = []
    for link in doc.get("links", []):
        source = link["source"]
        target = link["target"]
        relationship = link.get("relation", "")
        row = {
            "id": _edge_id(source, target, relationship),
            "source_id": source,
            "target_id": target,
            "relationship": relationship,
        }
        if "weight" in link:
            row["weight"] = link["weight"]
        edge_rows.append(row)

    store.load("code-node", node_rows)
    store.load("code-edge", edge_rows)


def main(argv: list[str]) -> int:
    from .cozo_store import CozoStore

    if len(argv) < 2:
        print("usage: project_graphify.py <graph.json>", file=sys.stderr)
        return 2
    schema = Path(__file__).resolve().parent.parent / "assets" / "kg-schema.edn"
    store = CozoStore.in_memory(schema_path=schema)
    project_graphify(Path(argv[1]), store)
    print("projected graphify graph.json into cozo store")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
