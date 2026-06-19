"""Deterministic code-to-claim autolinker for S6."""
from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable

from .cozo_store import CozoStore

CODE_FILE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".py",
    ".pyi",
    ".rs",
    ".ts",
    ".tsx",
}
TRAIL_RELATIONSHIPS = {"contains", "uses"}
_BACKTICK_SYMBOL = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)`")
_DOTTED_SYMBOL = re.compile(r"(?<![`A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)(?![`A-Za-z0-9_])")


@dataclass(frozen=True)
class CodeNode:
    id: str
    label: str | None
    source_file: str | None


@dataclass(frozen=True)
class CodeEdge:
    source: str
    target: str
    relationship: str


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    source_files: tuple[str, ...]


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def canonical_autolink_result(result: dict[str, list[dict[str, Any]]]) -> str:
    """Canonical JSON for result-set equality of links and evidence."""
    payload = {
        key: sorted(
            (dict(row) for row in result.get(key, [])),
            key=lambda row: _json(row),
        )
        for key in ("canonical_links", "link_evidence")
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _normalize_path(value: str | None) -> str | None:
    if not value:
        return None
    text = value.replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    parts = [part for part in text.split("/") if part and part != "."]
    if not parts:
        return None
    return "/".join(parts)


def _looks_like_code_file(value: str | None) -> bool:
    normalized = _normalize_path(value)
    if normalized is None:
        return False
    return PurePosixPath(normalized).suffix in CODE_FILE_SUFFIXES


def _code_nodes(store: CozoStore) -> dict[str, CodeNode]:
    rows = store.query("?[id, label, source_file] := *code_node{id, label, source_file}")
    return {
        str(row[0]): CodeNode(
            id=str(row[0]),
            label=str(row[1]) if row[1] is not None else None,
            source_file=_normalize_path(str(row[2])) if row[2] is not None else None,
        )
        for row in sorted(rows)
    }


def _code_edges(store: CozoStore) -> list[CodeEdge]:
    rows = store.query(
        "?[source_id, target_id, relationship] := "
        "*code_edge{source_id, target_id, relationship}"
    )
    return [
        CodeEdge(source=str(row[0]), target=str(row[1]), relationship=str(row[2]))
        for row in sorted(rows)
    ]


def _source_paths(store: CozoStore) -> dict[str, str]:
    rows = store.query("?[id, path] := *source{id, path}")
    return {
        str(row[0]): normalized
        for row in rows
        if row[1] is not None
        for normalized in [_normalize_path(str(row[1]))]
        if normalized is not None and _looks_like_code_file(normalized)
    }


def _claims(store: CozoStore) -> dict[str, Claim]:
    claim_rows = store.query("?[id, canonical_text] := *claim{id, canonical_text}")
    span_rows = store.query("?[claim_id, doc_id] := *source_span{claim_id, doc_id}")
    source_paths = _source_paths(store)
    files_by_claim: dict[str, set[str]] = defaultdict(set)
    for claim_id, doc_id in span_rows:
        if doc_id is None:
            continue
        normalized_doc = _normalize_path(str(doc_id))
        if _looks_like_code_file(normalized_doc):
            files_by_claim[str(claim_id)].add(str(normalized_doc))
        mapped = source_paths.get(str(doc_id))
        if mapped is not None:
            files_by_claim[str(claim_id)].add(mapped)
    claims: dict[str, Claim] = {}
    for claim_id, text in sorted(claim_rows):
        claims[str(claim_id)] = Claim(
            id=str(claim_id),
            text=str(text or ""),
            source_files=tuple(sorted(files_by_claim.get(str(claim_id), set()))),
        )
    return claims


def _is_module_node(node: CodeNode, source_file: str) -> bool:
    if node.source_file != source_file:
        return False
    basename = PurePosixPath(source_file).name
    labels = {
        value
        for raw in (node.label, node.id)
        for value in [_normalize_path(raw)]
        if value is not None
    }
    return source_file in labels or basename in labels


def _symbol_aliases(node: CodeNode) -> set[str]:
    aliases = {node.id}
    if node.label:
        aliases.add(node.label)
        if node.label.endswith("()"):
            aliases.add(node.label[:-2])
    return aliases


def _symbol_index(nodes: dict[str, CodeNode]) -> dict[str, list[CodeNode]]:
    index: dict[str, list[CodeNode]] = defaultdict(list)
    for node in nodes.values():
        for alias in _symbol_aliases(node):
            index[alias].append(node)
    return {symbol: sorted(matches, key=lambda node: node.id) for symbol, matches in index.items()}


def _mentions(text: str) -> list[str]:
    found = set(_BACKTICK_SYMBOL.findall(text))
    found.update(_DOTTED_SYMBOL.findall(text))
    return sorted(found)


def _incoming_trail_index(edges: Iterable[CodeEdge]) -> dict[str, list[CodeEdge]]:
    incoming: dict[str, list[CodeEdge]] = defaultdict(list)
    for edge in edges:
        if edge.relationship.lower() in TRAIL_RELATIONSHIPS:
            incoming[edge.target].append(edge)
    return {
        target: sorted(
            values,
            key=lambda edge: (edge.source, edge.relationship.lower(), edge.target),
        )
        for target, values in incoming.items()
    }


def _trail_to(node_id: str, incoming: dict[str, list[CodeEdge]]) -> list[dict[str, str]]:
    queue = deque([(node_id, [])])
    visited = {node_id}
    while queue:
        current, trail = queue.popleft()
        parents = incoming.get(current, [])
        if trail and not parents:
            return [
                {
                    "source": edge.source,
                    "relationship": edge.relationship.lower(),
                    "target": edge.target,
                }
                for edge in trail
            ]
        for edge in parents:
            if edge.source in visited:
                continue
            visited.add(edge.source)
            queue.append((edge.source, [edge, *trail]))
    return []


def _link_id(code_id: str, claim_id: str, kind: str) -> str:
    return f"{code_id}\x1f{claim_id}\x1f{kind}"


def _evidence_id(kind: str, code_id: str, claim_id: str, suffix: str = "") -> str:
    tail = f":{suffix}" if suffix else ""
    return f"ev:{kind}:{code_id}:{claim_id}{tail}"


def _evidence_row(
    *,
    kind: str,
    code_id: str,
    claim_id: str,
    score: float,
    witness: str,
    provenance: str,
    promoted: bool,
    suffix: str = "",
) -> dict[str, Any]:
    return {
        "id": _evidence_id(kind, code_id, claim_id, suffix),
        "code_id": code_id,
        "claim_id": claim_id,
        "kind": kind,
        "score": score,
        "witness": witness,
        "provenance": provenance,
        "promoted": promoted,
    }


def _canonical_link(code_id: str, claim_id: str, kind: str) -> dict[str, str]:
    return {
        "id": _link_id(code_id, claim_id, kind),
        "code_id": code_id,
        "claim_id": claim_id,
        "kind": kind,
    }


def _file_path_candidates(
    claims: dict[str, Claim],
    nodes: dict[str, CodeNode],
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    links: list[dict[str, str]] = []
    evidence: list[dict[str, Any]] = []
    for claim in claims.values():
        for source_file in claim.source_files:
            matches = sorted(
                [
                    node
                    for node in nodes.values()
                    if _is_module_node(node, source_file)
                ],
                key=lambda node: node.id,
            )
            promoted = len(matches) == 1
            for node in matches:
                evidence.append(
                    _evidence_row(
                        kind="file-path",
                        code_id=node.id,
                        claim_id=claim.id,
                        score=1.0 if promoted else 0.75,
                        witness=source_file,
                        provenance="deterministic:file-path",
                        promoted=promoted,
                    )
                )
            if promoted:
                links.append(_canonical_link(matches[0].id, claim.id, "file-path"))
    return links, evidence


def _exact_symbol_candidates(
    claims: dict[str, Claim],
    nodes: dict[str, CodeNode],
    edges: list[CodeEdge],
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    links: list[dict[str, str]] = []
    evidence: list[dict[str, Any]] = []
    symbol_index = _symbol_index(nodes)
    incoming = _incoming_trail_index(edges)
    for claim in claims.values():
        for symbol in _mentions(claim.text):
            matches = symbol_index.get(symbol, [])
            if not matches:
                continue
            ambiguous = len(matches) > 1
            for node in matches:
                trail = _trail_to(node.id, incoming)
                witness = _json({"symbol": symbol, "trail": trail})
                promoted = (not ambiguous) and bool(trail)
                evidence.append(
                    _evidence_row(
                        kind="exact-symbol",
                        code_id=node.id,
                        claim_id=claim.id,
                        score=1.0 if promoted else (0.75 if trail else 0.5),
                        witness=witness,
                        provenance="deterministic:exact-symbol",
                        promoted=promoted,
                        suffix=symbol if ambiguous else "",
                    )
                )
                if promoted:
                    links.append(_canonical_link(node.id, claim.id, "exact-symbol"))
    return links, evidence


def _sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: _json(row))


def materialize_code_claim_links(store: CozoStore) -> dict[str, list[dict[str, Any]]]:
    """Derive canonical code-claim links and evidence from the projected graph."""
    nodes = _code_nodes(store)
    edges = _code_edges(store)
    claims = _claims(store)

    file_links, file_evidence = _file_path_candidates(claims, nodes)
    symbol_links, symbol_evidence = _exact_symbol_candidates(claims, nodes, edges)
    links = _sort_rows(file_links + symbol_links)
    evidence = _sort_rows(file_evidence + symbol_evidence)

    store.load("code-claim-link", links)
    store.load("link-evidence", evidence)
    return {"canonical_links": links, "link_evidence": evidence}
