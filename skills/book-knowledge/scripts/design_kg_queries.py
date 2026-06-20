"""Named design-intelligence graph queries (REQ-KG-051/052)."""
from __future__ import annotations

import json
from typing import Any

QUERY_NAMES = (
    "impact",
    "why",
    "coverage-gaps",
    "stale-docs",
    "untested-god-nodes",
    "claim-grounding",
    "ci-gates",
)


def _json(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"))


def _sorted(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=_json)


def _relation(store, relation: str, cols: list[str]) -> list[dict[str, Any]]:
    col_list = ", ".join(cols)
    script = f"?[{col_list}] := *{relation}{{{col_list}}}"
    return [dict(zip(cols, row)) for row in store.query(script)]


def _by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in rows}


def _requirements(store) -> list[dict[str, Any]]:
    return _relation(
        store,
        "design_requirement",
        [
            "id",
            "requirement_id",
            "capability",
            "status",
            "text",
            "source_path",
            "source_line",
        ],
    )


def _decisions(store) -> list[dict[str, Any]]:
    return _relation(
        store,
        "design_decision",
        ["id", "kind", "status", "text", "rationale", "source_path", "source_line"],
    )


def _scenarios(store) -> list[dict[str, Any]]:
    return _relation(
        store,
        "design_scenario",
        ["id", "requirement_id", "capability", "text", "source_path", "source_line"],
    )


def _tests(store) -> list[dict[str, Any]]:
    return _relation(
        store,
        "test_case",
        ["id", "name", "framework", "target", "source_path", "source_line"],
    )


def _ci_jobs(store) -> list[dict[str, Any]]:
    return _relation(
        store,
        "ci_job",
        [
            "id",
            "workflow_id",
            "name",
            "required",
            "selector",
            "command",
            "source_path",
            "source_line",
        ],
    )


def _code_nodes(store) -> list[dict[str, Any]]:
    return _relation(
        store,
        "code_node",
        ["id", "label", "source_file", "rank", "community"],
    )


def _trace_links(store) -> list[dict[str, Any]]:
    return _relation(
        store,
        "traceability_link",
        [
            "id",
            "from_id",
            "to_id",
            "kind",
            "confidence",
            "witness",
            "provenance",
            "promoted",
            "source_path",
            "source_line",
        ],
    )


def _claims(store) -> list[dict[str, Any]]:
    return _relation(
        store,
        "claim",
        ["id", "canonical_text", "status"],
    )


def _code_claim_links(store) -> list[dict[str, Any]]:
    return _relation(
        store,
        "code_claim_link",
        ["id", "code_id", "claim_id", "kind"],
    )


def _promoted_links(store) -> list[dict[str, Any]]:
    return [row for row in _trace_links(store) if row["promoted"] is True]


def _promoted_trace_signatures(store) -> set[tuple[str, str, str]]:
    return {
        (str(row["kind"]), str(row["from_id"]), str(row["to_id"]))
        for row in _promoted_links(store)
    }


def _matching_code_ids(store, target: str) -> set[str]:
    needle = target.lower()
    matches: set[str] = set()
    for node in _code_nodes(store):
        haystack = " ".join(
            str(node.get(part) or "") for part in ("id", "label", "source_file")
        ).lower()
        if needle in haystack:
            matches.add(str(node["id"]))
    return matches


def impact(store, target: str) -> list[dict[str, Any]]:
    """Return promoted design/test/CI evidence that touches a code target."""
    code_ids = _matching_code_ids(store, target)
    rows: list[dict[str, Any]] = []
    for link in _promoted_links(store):
        if link["from_id"] not in code_ids and link["to_id"] not in code_ids:
            continue
        rows.append(
            {
                "query": "impact",
                "kind": link["kind"],
                "from_id": link["from_id"],
                "to_id": link["to_id"],
                "witness": link["witness"],
                "provenance": link["provenance"],
                "source_path": link["source_path"],
                "source_line": link["source_line"],
            }
        )
    return _sorted(rows)


def why(store, target: str) -> list[dict[str, Any]]:
    """Return source-backed requirements and promoted links explaining a target."""
    rows: list[dict[str, Any]] = []
    requirements = _requirements(store)
    matched_req_ids = {
        row["id"]
        for row in requirements
        if target in {row["id"], row["requirement_id"], row["capability"]}
    }
    for req in requirements:
        if req["id"] not in matched_req_ids:
            continue
        rows.append(
            {
                "query": "why",
                "kind": "requirement",
                "requirement_id": req["requirement_id"],
                "capability": req["capability"],
                "text": req["text"],
                "source_path": req["source_path"],
                "source_line": req["source_line"],
            }
        )
    for scenario in _scenarios(store):
        if target not in {
            scenario["id"],
            scenario["requirement_id"],
            scenario["capability"],
        }:
            continue
        rows.append(
            {
                "query": "why",
                "kind": "scenario",
                "requirement_id": scenario["requirement_id"],
                "capability": scenario["capability"],
                "text": scenario["text"],
                "source_path": scenario["source_path"],
                "source_line": scenario["source_line"],
            }
        )

    code_ids = _matching_code_ids(store, target)
    for link in _promoted_links(store):
        if (
            link["from_id"] not in matched_req_ids
            and link["to_id"] not in matched_req_ids
            and link["from_id"] not in code_ids
            and link["to_id"] not in code_ids
        ):
            continue
        rows.append(
            {
                "query": "why",
                "kind": link["kind"],
                "from_id": link["from_id"],
                "to_id": link["to_id"],
                "witness": link["witness"],
                "provenance": link["provenance"],
                "source_path": link["source_path"],
                "source_line": link["source_line"],
            }
        )
    return _sorted(rows)


def coverage_gaps(store) -> list[dict[str, Any]]:
    """Return requirements lacking promoted implementation/test/CI coverage."""
    required_kinds = {
        "implementation": "requirement-implemented-by",
        "test": "requirement-covered-by",
        "ci": "requirement-gated-by",
    }
    links_by_req: dict[str, set[str]] = {}
    for link in _promoted_links(store):
        links_by_req.setdefault(str(link["from_id"]), set()).add(str(link["kind"]))

    rows: list[dict[str, Any]] = []
    for req in _requirements(store):
        present = links_by_req.get(str(req["id"]), set())
        missing = [
            label
            for label, kind in required_kinds.items()
            if kind not in present
        ]
        if not missing:
            continue
        rows.append(
            {
                "query": "coverage-gaps",
                "kind": "coverage-gap",
                "requirement_id": req["requirement_id"],
                "capability": req["capability"],
                "missing": ",".join(missing),
                "source_path": req["source_path"],
                "source_line": req["source_line"],
            }
        )
    return _sorted(rows)


def stale_docs(store) -> list[dict[str, Any]]:
    """Return evidence-only design links that need review before use."""
    promoted = _promoted_trace_signatures(store)
    rows: list[dict[str, Any]] = []
    for link in _trace_links(store):
        if link["promoted"] is True:
            continue
        signature = (str(link["kind"]), str(link["from_id"]), str(link["to_id"]))
        if signature in promoted:
            continue
        rows.append(
            {
                "query": "stale-docs",
                "kind": "evidence-only-link",
                "from_id": link["from_id"],
                "to_id": link["to_id"],
                "link_kind": link["kind"],
                "witness": link["witness"],
                "provenance": link["provenance"],
                "source_path": link["source_path"],
                "source_line": link["source_line"],
            }
        )
    return _sorted(rows)


def untested_god_nodes(store, min_rank: float = 0.9) -> list[dict[str, Any]]:
    """Return high-rank code nodes with no promoted test-exercises-code link."""
    tested = {
        str(link["to_id"])
        for link in _promoted_links(store)
        if link["kind"] == "test-exercises-code"
    }
    rows: list[dict[str, Any]] = []
    for node in _code_nodes(store):
        rank = node.get("rank")
        if rank is None or float(rank) < min_rank or node["id"] in tested:
            continue
        rows.append(
            {
                "query": "untested-god-nodes",
                "kind": "untested-god-node",
                "code_id": node["id"],
                "label": node["label"],
                "source_path": node["source_file"] or "code-node",
                "source_line": 1,
                "rank": float(rank),
            }
        )
    return _sorted(rows)


def claim_grounding(store, target: str) -> list[dict[str, Any]]:
    """Return code-claim links for a code or claim target."""
    nodes = _by_id(_code_nodes(store))
    claims = _by_id(_claims(store))
    code_ids = _matching_code_ids(store, target)
    rows: list[dict[str, Any]] = []
    for link in _code_claim_links(store):
        if target not in {link["claim_id"], link["code_id"]} and link["code_id"] not in code_ids:
            continue
        node = nodes.get(str(link["code_id"]), {})
        claim = claims.get(str(link["claim_id"]), {})
        rows.append(
            {
                "query": "claim-grounding",
                "kind": "claim-supported-by-code",
                "code_id": link["code_id"],
                "code_label": node.get("label"),
                "claim_id": link["claim_id"],
                "claim_status": claim.get("status"),
                "claim_text": claim.get("canonical_text"),
                "link_kind": link.get("kind"),
                "source_path": node.get("source_file") or "code-node",
                "source_line": 1,
            }
        )
    return _sorted(rows)


def ci_gates(store, target: str) -> list[dict[str, Any]]:
    """Return CI jobs gating a requirement, capability, or requirement path."""
    requirements = _by_id(_requirements(store))
    jobs = _by_id(_ci_jobs(store))
    matched_req_ids = {
        req["id"]
        for req in requirements.values()
        if target in {req["id"], req["requirement_id"], req["capability"]}
        or target in str(req["source_path"])
    }
    rows: list[dict[str, Any]] = []
    for link in _promoted_links(store):
        if link["kind"] != "requirement-gated-by" or link["from_id"] not in matched_req_ids:
            continue
        req = requirements[str(link["from_id"])]
        job = jobs.get(str(link["to_id"]), {})
        rows.append(
            {
                "query": "ci-gates",
                "kind": "requirement-gated-by",
                "requirement_id": req["requirement_id"],
                "capability": req["capability"],
                "ci_job_id": link["to_id"],
                "ci_job_name": job.get("name"),
                "required": job.get("required"),
                "selector": job.get("selector"),
                "command": job.get("command"),
                "source_path": link["source_path"],
                "source_line": link["source_line"],
            }
        )
    return _sorted(rows)


def run_design_query(store, name: str, target: str | None = None) -> list[dict[str, Any]]:
    """Run one named design-intelligence query."""
    if name == "impact":
        if target is None:
            raise ValueError("impact requires a target")
        return impact(store, target)
    if name == "why":
        if target is None:
            raise ValueError("why requires a target")
        return why(store, target)
    if name == "coverage-gaps":
        return coverage_gaps(store)
    if name == "stale-docs":
        return stale_docs(store)
    if name == "untested-god-nodes":
        return untested_god_nodes(store)
    if name == "claim-grounding":
        if target is None:
            raise ValueError("claim-grounding requires a target")
        return claim_grounding(store, target)
    if name == "ci-gates":
        if target is None:
            raise ValueError("ci-gates requires a target")
        return ci_gates(store, target)
    raise KeyError(f"unknown design query {name!r}")
