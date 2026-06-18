"""Project structured chapter retrieval bundles from the Cozo graph."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote

import edn_format
import jsonschema

from .cozo_store import CozoStore
from .project_ledger_cozo import project_ledger
from .workspace import WorkspaceLayout

ASSETS = Path(__file__).resolve().parent.parent / "assets"
KG_SCHEMA = ASSETS / "kg-schema.edn"
BUNDLE_SCHEMA = ASSETS / "chapter-retrieval-bundle.schema.json"
_CHAPTER_BASE = "https://example.org/book-knowledge/chapters/"


def chapter_uri(chapter_id: str) -> str:
    """Return the full chapter URI used by claim-chapter rows."""
    return f"{_CHAPTER_BASE}{quote(chapter_id)}"


def _chapter_evidence_edn(uri: str) -> str:
    return (
        "(defquery :chapter-evidence "
        ":find [?claim-id] "
        ":where [[?cc :claim-chapter/claim-id ?claim-id] "
        f'[?cc :claim-chapter/chapter "{uri}"] '
        "[?c :claim/id ?claim-id] "
        '[?c :claim/status "verified"]])'
    )


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _edn_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {edn_format.Keyword(str(k)): _edn_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_edn_value(v) for v in value]
    return value


def _edn(payload: dict[str, Any]) -> str:
    return edn_format.dumps(_edn_value(payload)) + "\n"


def bundle_payload_canonical(payload: dict[str, Any]) -> dict[str, Any]:
    """Canonical dict form for deterministic comparisons and goldens."""
    return json.loads(_json(payload))


def validate_bundle_payload(payload: dict[str, Any]) -> None:
    schema = json.loads(BUNDLE_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)


def _claims_by_id(store: CozoStore) -> dict[str, dict[str, Any]]:
    rows = store.query(
        "?[id, canonical_text, status, claim_type, confidence, load_bearing] := "
        "*claim{id, canonical_text, status, claim_type, confidence, load_bearing}"
    )
    return {
        row[0]: {
            "id": row[0],
            "text": row[1],
            "status": row[2],
            "claim_type": row[3],
            "confidence": row[4],
            "load_bearing": bool(row[5]),
        }
        for row in rows
    }


def _spans_by_claim(store: CozoStore) -> dict[str, list[dict[str, Any]]]:
    rows = store.query(
        "?[id, claim_id, doc_id, node_id, page_index, locator_text] := "
        "*source_span{id, claim_id, doc_id, node_id, page_index, locator_text}"
    )
    spans: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        item = {
            "span-id": row[0],
            "claim-id": row[1],
            "doc-id": row[2],
            "node-id": row[3],
            "page-index": row[4],
            "locator-text": row[5],
        }
        spans[row[1]].append(item)
    for claim_id in spans:
        spans[claim_id].sort(key=lambda s: s["span-id"])
    return dict(spans)


def _code_links(store: CozoStore, selected: set[str]) -> dict[str, list[dict[str, str]]]:
    rows = store.query("?[code_id, claim_id] := *code_claim_link{code_id, claim_id}")
    links: dict[str, list[dict[str, str]]] = defaultdict(list)
    for code_id, claim_id in rows:
        if claim_id in selected:
            links[claim_id].append({"code-id": code_id})
    return {
        claim_id: sorted(items, key=lambda item: item["code-id"])
        for claim_id, items in sorted(links.items())
        if items
    }


def _dominant_communities(
    store: CozoStore, selected_load_bearing: set[str]
) -> list[dict[str, Any]]:
    code_rows = store.query("?[id, community] := *code_node{id, community}")
    community_by_code = {row[0]: row[1] for row in code_rows if row[1] is not None}
    link_rows = store.query("?[code_id, claim_id] := *code_claim_link{code_id, claim_id}")
    claims_by_community: dict[str, set[str]] = defaultdict(set)
    for code_id, claim_id in link_rows:
        community_id = community_by_code.get(code_id)
        if community_id is not None and claim_id in selected_load_bearing:
            claims_by_community[community_id].add(claim_id)

    ranked = sorted(
        (
            (community_id, sorted(claim_ids))
            for community_id, claim_ids in claims_by_community.items()
        ),
        key=lambda item: (-len(item[1]), item[0]),
    )
    return [
        {
            "rank": idx,
            "community-id": community_id,
            "claim-count": len(claim_ids),
            "claim-ids": claim_ids,
        }
        for idx, (community_id, claim_ids) in enumerate(ranked, start=1)
    ]


def _unresolved_rebuttals(
    store: CozoStore, selected_load_bearing: set[str]
) -> list[dict[str, Any]]:
    rows = store.query(
        "?[id, target_claim_id, cc_status, created_at] := "
        "*counter_claim{id, target_claim_id, cc_status, created_at}"
    )
    rebuttals = [
        {
            "counter-claim-id": row[0],
            "target-claim-id": row[1],
            "status": row[2],
            "created-at": row[3],
        }
        for row in rows
        if row[1] in selected_load_bearing and row[2] == "open"
    ]
    return sorted(
        rebuttals,
        key=lambda item: (item["target-claim-id"], item["counter-claim-id"]),
    )


def _load_bearing_claims(
    selected_ids: list[str],
    claims: dict[str, dict[str, Any]],
    spans: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows = [claims[cid] for cid in selected_ids if claims.get(cid, {}).get("load_bearing")]
    rows.sort(key=lambda c: (-(c["confidence"] or 0.0), c["id"]))
    return [
        {
            "claim-id": claim["id"],
            "text": claim["text"],
            "status": claim["status"],
            "confidence": claim["confidence"],
            "source-span-ids": [s["span-id"] for s in spans.get(claim["id"], [])],
        }
        for claim in rows
    ]


def _minimal_span_anchors(
    load_bearing: list[dict[str, Any]],
    spans: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    anchors: list[dict[str, Any]] = []
    unanchored: list[dict[str, str]] = []
    for claim in sorted(load_bearing, key=lambda item: item["claim-id"]):
        claim_id = claim["claim-id"]
        claim_spans = spans.get(claim_id, [])
        if not claim_spans:
            unanchored.append({"claim-id": claim_id, "reason": "no-source-span"})
            continue
        anchors.append(claim_spans[0])
    anchors.sort(key=lambda item: (item["claim-id"], item["span-id"]))
    return anchors, unanchored


def _prompt_scaffold(payload: dict[str, Any]) -> str:
    claim_ids = [c["claim-id"] for c in payload["load-bearing-claims"]]
    anchor_pairs = [
        f"{a['claim-id']}->{a['span-id']}" for a in payload["source-span-anchors"]
    ]
    rebuttals = [
        f"{r['counter-claim-id']} targets {r['target-claim-id']}"
        for r in payload["unresolved-rebuttals"]
    ]
    lines = [
        f"Chapter {payload['chapter-id']} retrieval bundle.",
        "State the chapter thesis before drafting.",
        "Present support claims in order: " + (", ".join(claim_ids) or "(none)"),
        "Anchor support claims to spans: " + (", ".join(anchor_pairs) or "(none)"),
    ]
    if rebuttals:
        lines.append("Caveat unresolved rebuttals: " + "; ".join(rebuttals))
    else:
        lines.append("No unresolved rebuttals are in scope.")
    return "\n".join(lines) + "\n"


def materialize_chapter_bundle(store: CozoStore, chapter_id: str) -> dict[str, Any]:
    """Materialize and return one bundle row from an already-loaded store."""
    uri = chapter_uri(chapter_id)
    selected_ids = sorted({row[0] for row in store.query_edn(_chapter_evidence_edn(uri))})
    claims = _claims_by_id(store)
    spans = _spans_by_claim(store)
    load_bearing = _load_bearing_claims(selected_ids, claims, spans)
    selected_load_bearing = {c["claim-id"] for c in load_bearing}
    anchors, unanchored = _minimal_span_anchors(load_bearing, spans)

    payload: dict[str, Any] = {
        "schema": "chapter-retrieval-bundle/v1",
        "chapter-id": chapter_id,
        "chapter-uri": uri,
        "dominant-communities": _dominant_communities(store, selected_load_bearing),
        "load-bearing-claims": load_bearing,
        "unresolved-rebuttals": _unresolved_rebuttals(store, selected_load_bearing),
        "source-span-anchors": anchors,
    }
    links = _code_links(store, selected_load_bearing)
    if links:
        payload["code-links"] = links
    if unanchored:
        payload["flags"] = {"unanchored-load-bearing": unanchored}

    validate_bundle_payload(payload)
    payload_json = _json(payload)
    payload_edn = _edn(payload)
    prompt = _prompt_scaffold(payload)
    row = {
        "id": f"bundle:{chapter_id}",
        "chapter_id": chapter_id,
        "chapter_uri": uri,
        "payload": payload,
        "payload_json": payload_json,
        "payload_edn": payload_edn,
        "prompt_scaffold": prompt,
    }
    store.load(
        "chapter-retrieval-bundle",
        [
            {
                "id": row["id"],
                "chapter_id": row["chapter_id"],
                "chapter_uri": row["chapter_uri"],
                "payload_json": payload_json,
                "payload_edn": payload_edn,
                "prompt_scaffold": prompt,
            }
        ],
    )
    return row


def project_chapter_bundle(
    layout: WorkspaceLayout | Path, chapter_id: str, store: CozoStore | None = None
) -> dict[str, Any]:
    """Project ledger data into a store, then materialize one chapter bundle."""
    workspace = layout if isinstance(layout, WorkspaceLayout) else WorkspaceLayout(Path(layout))
    if store is None:
        store = CozoStore.in_memory(schema_path=KG_SCHEMA)
    project_ledger(workspace, store)
    return materialize_chapter_bundle(store, chapter_id)
