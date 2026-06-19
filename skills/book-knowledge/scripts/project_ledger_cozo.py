"""Project the claim ledger into the Cozo store (REQ-KG-004).

`project_ledger(layout, store)` loads every latest-per-id NON-SUPERSEDED claim
and its source-spans from the append-only ledger into the store's ``claim`` and
``source-span`` relations. The ledger is read-only here: it is never opened for
writing. This is the relational counterpart of :mod:`project_graph` (the RDF/TriG
emit), which stays in parallel and is NOT replaced.

Inclusion filter (mirrors :func:`project_graph.project_graph` exactly so the Cozo
node set equals the RDF node set): collapse the append-only ledger to one record
per ``claim_id`` (last write wins) with ``latest_per``, then keep every record
whose latest ``status`` is NOT ``"superseded"``. Note this is the *only* status
dropped: ``refuted`` (the other terminal state) IS projected, matching
``project_graph``, which skips solely ``superseded``. Per-query status filtering
(e.g. ``contradiction_scan``, ``posterior-floor``) is left to the SPARQL/Cozo
query layer, so each projected ``claim`` row carries its ``status`` column.

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

Chapter coverage (REQ-KG-006): a claim's ``supports_chapters`` list is the
ledger form of project_graph's ``tbf:supportsChapter`` triples. It is projected
into two relations so a chapter can be grouped/counted relationally:
  - ``claim-chapter`` gets one row per (claim, chapter), with ``chapter`` set to
    the SAME full chapter URI project_graph mints
    (``{BASE}chapters/<id>``) so the Cozo coverage query reproduces the SPARQL
    bindings exactly, plus the owning ``claim_id`` for the status join.
  - ``chapter`` gets one row per distinct chapter URI referenced (the relational
    counterpart of the ``?chapter a tbf:Chapter`` declaration).

Conflict edges (REQ-KG-006): a claim's ``conflicts_with`` list is the ledger
form of project_graph's ``tbf:conflictsWith`` triples. It is projected into the
``claim-conflict`` relation, one row per (claim, target), DIRECTIONAL — the
reverse edge appears only if the target itself declares the conflict — mirroring
project_graph's once-per-target emission exactly. ``claim_id`` is the declaring
claim, ``other_id`` the conflicting target; the synthetic ``(claim_id . other_id)``
pair id is the identity so re-projection upserts.

Counter-claims (REQ-KG-006): the parallel counter-claim ledger
(``claims/counter-claims.jsonl``) projects into the ``counter-claim`` relation as
ONE row per cc carrying its LATEST status (P5.2 canonical: dedupe-to-latest-per-id
via ``latest_per``), keyed by the bare cc id. A cc that went ``open -> addressed``
lands as ``addressed``; an ``addressed -> open`` reopen lands as ``open`` (the
rebuttal-presence gate acts on the current status). The record ``status`` maps to
the ``cc-status`` column (renamed so it does not collide with a claim's status);
``target_claim_id`` (the rebut target) is kept bare so it joins ``claim.id``.

Typed values pass through untouched: ``cozo_store`` columns are typed from the
schema ``:types`` (Float/Int/Bool), and ``load`` preserves the Python value, so
floats/bools/ints from the ledger land as real typed cells.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from .counter_claims import read_counter_claims
from .io_utils import latest_per, read_jsonl
from .normalized_claims import normalized_rows_for_claim
from .workspace import WorkspaceLayout

# Mirror project_graph's chapter URI minting so the relational chapter
# coverage facts carry the same identifiers as the RDF projection.
_BASE = "https://example.org/book-knowledge/"


def _chapter_uri(chapter: str) -> str:
    """Full chapter URI, identical to project_graph's ``{BASE}chapters/<id>``."""
    return f"{_BASE}chapters/{quote(chapter)}"


def _wiki_page_uri(rel_to_wiki: str) -> str:
    """Full wiki-page URI: ``{BASE}wiki/<path-relative-to-wiki-dir>``.

    P5.2 canonical decision: drop project_graph's (intentional) doubled ``wiki/``
    prefix. project_graph minted ``{BASE}wiki/{rel_to_ROOT}`` where rel_to_root
    already started with ``wiki/`` (giving ``.../wiki/wiki/...``); the Cozo
    projection used to mirror that quirk byte-for-byte. The canonical form keys the
    page on its path RELATIVE TO THE WIKI DIR, so ``.../wiki/concepts/foo.md`` —
    one ``wiki/``. The legacy RDF emit keeps the quirk until it is deleted in P5.4;
    no test compares the two (the query-port goldens run the Cozo path only, and
    bermuda has no wiki pages so its golden is unaffected).
    """
    return f"{_BASE}wiki/{quote(rel_to_wiki.replace(chr(92), '/'))}"


def _collect_wiki_pages(layout: WorkspaceLayout) -> tuple[list[dict], dict[str, str]]:
    """Scan ``wiki/**/*.md`` and return (wiki_page rows, doc_id->page_uri index).

    Mirrors :func:`project_graph.project_graph`'s per-file ``tbf:WikiPage``
    emission: one row per md file, ``id`` the full page URI, ``path`` the
    forward-slashed path relative to the workspace root, ``title`` the file stem.

    The second return value maps a page's path RELATIVE TO THE WIKI DIR (e.g.
    ``concepts/foo.md``) to its full URI. That relative path is the natural
    identifier a claim's source span ``doc_id`` carries when the claim is sourced
    from a wiki page, so it is the key used to back-link a span to its page (the
    relational form of ``?claim tbf:hasSourceSpan ?page``).
    """
    rows: list[dict] = []
    by_doc_id: dict[str, str] = {}
    wiki_dir = layout.wiki
    if not wiki_dir.exists():
        return rows, by_doc_id
    for md_file in sorted(wiki_dir.rglob("*.md")):
        rel_to_root = str(md_file.relative_to(layout.root)).replace(chr(92), "/")
        rel_to_wiki = str(md_file.relative_to(wiki_dir)).replace(chr(92), "/")
        # Canonical (P5.2): key the page URI on its path relative to the WIKI dir,
        # so a single ``wiki/`` prefix (not project_graph's doubled ``wiki/wiki/``).
        page_uri = _wiki_page_uri(rel_to_wiki)
        rows.append(
            {"id": page_uri, "path": rel_to_root, "title": md_file.stem}
        )
        by_doc_id[rel_to_wiki] = page_uri
    return rows, by_doc_id

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


# source-relation columns we copy from a manifest (snake spelling matches the
# schema attrs). The manifest ``doc_id`` maps to the source identity column ``id``
# and ``ingested_at`` to ``ingested_at`` (schema:dateCreated in the RDF emit).
_SOURCE_FIELDS = ("path", "title", "trust")


def _canonical_utc_timestamp(value):
    """Normalize aware ISO-8601 timestamps to one UTC string form."""
    if not isinstance(value, str):
        return value
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if dt.tzinfo is None:
        return value
    return dt.astimezone(timezone.utc).isoformat()


def _collect_sources(layout: WorkspaceLayout) -> list[dict]:
    """Scan ``raw/manifests/*.json`` and return one ``source`` row per manifest.

    Mirrors :func:`project_graph.project_graph`'s manifest pass: it reads each
    manifest, keys the source on the manifest ``doc_id``, and carries the
    ``ingested_at`` date (project_graph emits ``<src> schema:dateCreated
    <ingested_at>``). A manifest lacking ``doc_id`` is skipped, matching
    project_graph (which only emits when both ``doc_id`` and ``ingested_at`` are
    present). The ``doc_id`` is the natural key a claim's source span carries in
    its ``doc_id`` column, so the claim->span->source join (the relational form of
    ``?claim prov:wasDerivedFrom ?src``) keys off it.
    """
    rows: list[dict] = []
    seen: set[str] = set()
    manifest_dir = layout.manifests
    if not manifest_dir.exists():
        return rows
    for mf in sorted(manifest_dir.glob("*.json")):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        doc_id = data.get("doc_id")
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        row: dict = {"id": doc_id}
        if "ingested_at" in data:
            row["ingested_at"] = _canonical_utc_timestamp(data["ingested_at"])
        for field in _SOURCE_FIELDS:
            if field in data:
                row[field] = data[field]
        rows.append(row)
    return rows


def project_ledger(layout: WorkspaceLayout, store) -> None:
    """Load latest-per-id non-superseded claims + their spans into ``store``.

    Reads ``layout.ledger`` (never writes it), collapses to one record per
    ``claim_id`` (last write wins), drops only records whose latest
    ``status == "superseded"`` (mirroring :func:`project_graph.project_graph`),
    and upserts a ``claim`` row plus its ``source-span`` rows for each. The
    ``status`` column rides along on every claim row so downstream queries can
    apply their own per-status filtering.
    """
    latest = latest_per(read_jsonl(layout.ledger), "claim_id")

    # Wiki pages are scanned from wiki/**/*.md, mirroring project_graph. The
    # doc_id index lets a span back-link to a page it sources (see _SPAN below).
    wiki_page_rows, page_by_doc_id = _collect_wiki_pages(layout)

    claim_rows: list[dict] = []
    span_rows: list[dict] = []
    claim_chapter_rows: list[dict] = []
    chapter_rows: dict[str, dict] = {}  # uri -> row (dedup distinct chapters)
    claim_conflict_rows: list[dict] = []
    claim_quantity_rows: list[dict] = []
    claim_unit_rows: list[dict] = []
    claim_time_interval_rows: list[dict] = []
    claim_normal_form_rows: list[dict] = []

    for record in latest.values():
        if record.get("status") == "superseded":
            continue
        claim_id = record["claim_id"]

        row: dict = {"id": claim_id}
        for field in _CLAIM_FIELDS:
            if field in record:
                row[field] = (
                    _canonical_utc_timestamp(record[field])
                    if field in {"created_at", "last_verified_at"}
                    else record[field]
                )
        claim_rows.append(row)

        normalized = normalized_rows_for_claim(record)
        claim_quantity_rows.extend(normalized["claim-quantity"])
        claim_unit_rows.extend(normalized["claim-unit"])
        claim_time_interval_rows.extend(normalized["claim-time-interval"])
        claim_normal_form_rows.extend(normalized["claim-normal-form"])

        for chapter in record.get("supports_chapters", []):
            chapter_uri = _chapter_uri(chapter)
            claim_chapter_rows.append(
                {
                    "id": f"{claim_id}\x1f{chapter_uri}",
                    "claim_id": claim_id,
                    "chapter": chapter_uri,
                }
            )
            chapter_rows.setdefault(chapter_uri, {"id": chapter_uri})

        for other_id in record.get("conflicts_with", []):
            claim_conflict_rows.append(
                {
                    "id": f"{claim_id}\x1f{other_id}",
                    "claim_id": claim_id,
                    "other_id": other_id,
                }
            )

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
            # Back-link the span to a wiki page when its doc_id names one: this
            # is the relational form of ``?claim tbf:hasSourceSpan ?page`` that
            # orphan_wiki_pages negates against. Spans citing ordinary docs leave
            # wiki_page_id null.
            page_uri = page_by_doc_id.get(doc_id)
            if page_uri is not None:
                span_row["wiki_page_id"] = page_uri
            span_rows.append(span_row)

    # Counter-claims (REQ-KG-006). P5.2 canonical decision: one row per cc carrying
    # its LATEST status (dedupe-to-latest-per-id), replacing the prior distinct-
    # (cc-id, status) history set that mirrored project_graph's per-record
    # tbf:ccStatus emission. ``latest_per`` keeps the last-written record per cc id,
    # so a cc that went open -> addressed lands as "addressed"; an addressed -> open
    # reopen lands as "open" (and the rebuttal-presence gate then treats it as
    # unaddressed — the current lifecycle status is what the gate should act on).
    # Identity is the bare cc id. The legacy RDF emit keeps the full-history set
    # until it is deleted in P5.4; no test compares the two (the query-port goldens
    # run the Cozo path only). ``status`` maps to ``cc-status`` (renamed to
    # disambiguate from a claim's status).
    counter_claim_rows: list[dict] = []
    for cc in latest_per(read_counter_claims(layout.root), "id").values():
        cc_id = cc["id"]
        row = {
            "id": cc_id,
            "cc_id": cc_id,
            "target_claim_id": cc.get("target_claim_id"),
            "cc_status": cc.get("status"),
        }
        if "created_at" in cc:
            row["created_at"] = cc["created_at"]
        counter_claim_rows.append(row)

    store.load("claim", claim_rows)
    store.load("claim-quantity", claim_quantity_rows)
    store.load("claim-unit", claim_unit_rows)
    store.load("claim-time-interval", claim_time_interval_rows)
    store.load("claim-normal-form", claim_normal_form_rows)
    store.load("source-span", span_rows)
    # Source manifests (REQ-KG-006): one row per raw/manifests/*.json, mirroring
    # project_graph's schema:dateCreated emission. The claim->span->source join
    # (span.doc_id == source.id) is the relational form of prov:wasDerivedFrom,
    # and source.ingested_at is the schema:dateCreated the stale_after_source_refresh
    # port compares against the claim's created_at.
    store.load("source", _collect_sources(layout))
    store.load("claim-chapter", claim_chapter_rows)
    store.load("chapter", list(chapter_rows.values()))
    store.load("claim-conflict", claim_conflict_rows)
    store.load("counter-claim", counter_claim_rows)
    store.load("wiki-page", wiki_page_rows)
    # chapter_wiki_ref has no ledger-derived source today (project_graph emits no
    # tbf:referencesPage triples), so it is loaded empty. The relation exists so
    # the orphan port can express the chapter-reference negation arm faithfully.
    store.load("chapter-wiki-ref", [])
    # rebuttal_window_ok likewise has no ledger-derived source today (project_graph
    # emits no tbf:rebuttalWindowOk triples), so it is loaded empty. The relation
    # exists so the contested-rebuttal-window port can express its FILTER NOT
    # EXISTS arm faithfully: a never-emitted predicate => the negation clears
    # nothing => every disputed chapter-supporting claim surfaces.
    store.load("rebuttal-window-ok", [])
    # chapter_section has no production projector yet: in the C0.1 violating
    # fixture the tbf:ChapterSection / tbf:usesClaim triples were injected as raw
    # RDF only, with no ledger record behind them. So it is loaded empty here
    # (like chapter-wiki-ref), which keeps the bermuda workspace at 0 violations;
    # the violating parity test loads synthetic chapter-section rows directly. A
    # real chapter-section projector is future work (REQ-KG-012 chapter-cites-verified).
    store.load("chapter-section", [])


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
