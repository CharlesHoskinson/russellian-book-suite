"""Project the claim ledger into the Cozo store (REQ-KG-004).

`project_ledger(layout, store)` loads every latest-per-id VERIFIED claim and its
source-spans from the append-only ledger into the store's ``claim`` and
``source-span`` relations. The ledger is read-only here: it is never opened for
writing. This is the relational counterpart of :mod:`project_graph` (the RDF/TriG
emit), which stays in parallel and is NOT replaced.

Field mapping (ledger snake -> schema snake column):
  - claim record ``claim_id`` -> claim relation identity column ``id``.
  - everything else (``canonical_text``, ``confidence``, ...) already matches the
    snake spelling of the schema's kebab attrs, so ``CozoStore.load`` (which
    snake-normalizes keys) maps them straight through. Unknown ledger keys are
    ignored by ``load`` (it only keeps the relation's declared columns).

Source spans are nested objects in the ledger with no id of their own. Each
projected span gets:
  - ``claim_id`` = the owning claim's id (the back-reference added in P0.5 so the
    P1 claim<->span join / unsupported_claims negation is expressible), and
  - a deterministic minted ``id`` = a hash of (claim_id, doc_id, locator_text),
    stable across runs so re-projection upserts rather than duplicates.

Typed values pass through untouched: ``cozo_store`` columns are typed from the
schema ``:types`` (Float/Int/Bool), and ``load`` preserves the Python value, so
floats/bools/ints from the ledger land as real typed cells.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from .io_utils import latest_per, read_jsonl
from .workspace import WorkspaceLayout

# claim-relation columns we copy verbatim from the ledger record (snake spelling
# matches the schema attrs). ``id`` is mapped from ``claim_id`` separately.
_CLAIM_FIELDS = (
    "canonical_text",
    "status",
    "claim_type",
    "semantic_class",
    "confidence",
    "p_prior",
    "p_posterior",
    "load_bearing",
    "axiom",
    "pin_low_confidence",
    "created_at",
    "last_verified_at",
)

_SPAN_FIELDS = ("doc_id", "node_id", "page_index", "locator_text")


def _span_id(claim_id: str, doc_id: str, locator_text: str) -> str:
    """Deterministic, stable id for a nested source span.

    Spans have no id in the ledger; we mint one from the owning claim plus the
    span's natural key (doc + locator) so re-projection upserts the same row.
    """
    digest = hashlib.sha1(
        "\x1f".join((claim_id, doc_id, locator_text)).encode("utf-8")
    ).hexdigest()[:16]
    return f"span-{digest}"


def project_ledger(layout: WorkspaceLayout, store) -> None:
    """Load latest-per-id verified claims + their spans into ``store``.

    Reads ``layout.ledger`` (never writes it), collapses to one record per
    ``claim_id`` (last write wins), keeps only ``status == "verified"``, and
    upserts a ``claim`` row plus its ``source-span`` rows for each.
    """
    latest = latest_per(read_jsonl(layout.ledger), "claim_id")

    claim_rows: list[dict] = []
    span_rows: list[dict] = []

    for record in latest.values():
        if record.get("status") != "verified":
            continue
        claim_id = record["claim_id"]

        row: dict = {"id": claim_id}
        for field in _CLAIM_FIELDS:
            if field in record:
                row[field] = record[field]
        claim_rows.append(row)

        for span in record.get("source_spans", []):
            doc_id = span.get("doc_id", "")
            locator_text = span.get("locator_text", "")
            span_row: dict = {
                "id": _span_id(claim_id, doc_id, locator_text),
                "claim_id": claim_id,
            }
            for field in _SPAN_FIELDS:
                if field in span:
                    span_row[field] = span[field]
            span_rows.append(span_row)

    store.load("claim", claim_rows)
    store.load("source-span", span_rows)


def main(argv: list[str]) -> int:
    from .cozo_store import CozoStore

    if len(argv) < 2:
        print("usage: project_ledger_cozo.py <workspace-dir>", file=sys.stderr)
        return 2
    layout = WorkspaceLayout(Path(argv[1]))
    schema = Path(__file__).resolve().parent.parent / "assets" / "kg-schema.edn"
    store = CozoStore.in_memory(schema_path=schema)
    project_ledger(layout, store)
    print("projected ledger into cozo store")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
