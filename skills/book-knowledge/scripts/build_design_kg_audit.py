"""Build a reproducible design-intelligence KG audit artifact.

The artifact joins the graphify code graph with OpenSpec requirements, authored
design docs, tests, CI, and deterministic traceability links. It is meant for
agent and reviewer study: counts are machine-readable, while markdown files keep
the evidence paths easy to scan.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date as date_type
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
SCHEMA_PATH = SKILL_ROOT / "assets" / "kg-schema.edn"

if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts.cozo_store import CozoStore  # noqa: E402
from scripts.design_kg_queries import QUERY_NAMES, run_design_query  # noqa: E402
from scripts.project_design_kg import (  # noqa: E402
    project_design_docs,
    project_design_requirements,
    project_tests_and_ci,
    project_traceability_links,
)
from scripts.project_graphify import project_graphify  # noqa: E402

RELATION_COLUMNS = {
    "design_requirement": [
        "id",
        "requirement_id",
        "capability",
        "status",
        "text",
        "source_path",
        "source_line",
    ],
    "design_scenario": [
        "id",
        "requirement_id",
        "capability",
        "text",
        "source_path",
        "source_line",
    ],
    "design_decision": [
        "id",
        "kind",
        "status",
        "text",
        "rationale",
        "source_path",
        "source_line",
    ],
    "operator_command": [
        "id",
        "command",
        "shell",
        "purpose",
        "source_path",
        "source_line",
    ],
    "test_case": [
        "id",
        "name",
        "framework",
        "target",
        "source_path",
        "source_line",
    ],
    "ci_workflow": [
        "id",
        "name",
        "trigger",
        "source_path",
        "source_line",
    ],
    "ci_job": [
        "id",
        "workflow_id",
        "name",
        "required",
        "selector",
        "command",
        "source_path",
        "source_line",
    ],
    "traceability_link": [
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
    "code_node": [
        "id",
        "label",
        "source_file",
        "rank",
        "community",
    ],
    "code_edge": [
        "id",
        "source_id",
        "target_id",
        "relationship",
        "weight",
    ],
}


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _graphify_path(root: Path) -> Path | None:
    for rel in ("graphify/graph.json", "graphify-out/graph.json"):
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


def _graphify_report_path(root: Path) -> Path | None:
    for rel in ("graphify/GRAPH_REPORT.md", "graphify-out/GRAPH_REPORT.md"):
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


def _run_capture(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = (result.stdout or result.stderr).strip()
    return text.splitlines()[0].strip() if text else None


def _detect_commit(root: Path) -> str:
    return _run_capture(["git", "rev-parse", "--short", "HEAD"], root) or "unknown"


def _detect_graphify_version(root: Path) -> str:
    return _run_capture(
        [sys.executable, "-m", "graphify", "--version"],
        root,
    ) or "unknown"


def _relation(store: CozoStore, relation: str) -> list[dict[str, Any]]:
    cols = RELATION_COLUMNS[relation]
    col_list = ", ".join(cols)
    script = f"?[{col_list}] := *{relation}{{{col_list}}}"
    return [dict(zip(cols, row)) for row in store.query(script)]


def _build_store(root: Path) -> CozoStore:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    graph_path = _graphify_path(root)
    if graph_path is not None:
        project_graphify(graph_path, store)
    project_design_requirements(root, store)
    project_design_docs(root, store)
    project_tests_and_ci(root, store)
    project_traceability_links(root, store)
    return store


def _impact_target(
    code_nodes: list[dict[str, Any]],
    traceability_links: list[dict[str, Any]],
) -> str | None:
    by_id = {str(row["id"]): row for row in code_nodes}
    for link in sorted(traceability_links, key=lambda row: str(row["id"])):
        if link.get("promoted") is not True:
            continue
        for endpoint in ("to_id", "from_id"):
            node = by_id.get(str(link.get(endpoint)))
            if node is None:
                continue
            return str(node.get("source_file") or node.get("label") or node["id"])
    if code_nodes:
        row = sorted(code_nodes, key=lambda item: str(item["id"]))[0]
        return str(row.get("source_file") or row.get("label") or row["id"])
    return None


def _query_outputs(
    store: CozoStore,
    rows: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    requirements = rows["design_requirement"]
    target_req = requirements[0]["requirement_id"] if requirements else None
    target_capability = requirements[0]["capability"] if requirements else None
    target_impact = _impact_target(rows["code_node"], rows["traceability_link"])

    outputs: dict[str, list[dict[str, Any]]] = {}
    for name in QUERY_NAMES:
        try:
            if name == "impact":
                outputs[name] = (
                    run_design_query(store, name, target_impact)
                    if target_impact is not None
                    else []
                )
            elif name == "why":
                outputs[name] = (
                    run_design_query(store, name, target_req)
                    if target_req is not None
                    else []
                )
            elif name == "ci-gates":
                outputs[name] = (
                    run_design_query(store, name, target_capability)
                    if target_capability is not None
                    else []
                )
            elif name == "claim-grounding":
                outputs[name] = (
                    run_design_query(store, name, target_impact)
                    if target_impact is not None
                    else []
                )
            else:
                outputs[name] = run_design_query(store, name)
        except Exception as exc:  # pragma: no cover - defensive artifact note
            outputs[name] = [
                {
                    "query": name,
                    "kind": "query-error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "source_path": "audit-builder",
                    "source_line": 1,
                }
            ]
    return outputs


def _parse_communities(report_path: Path | None) -> list[dict[str, Any]]:
    if report_path is None:
        return []

    communities: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in report_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("### Community "):
            title = line[4:].strip()
            current = {"title": title, "node_count": 0, "sample_nodes": []}
            communities.append(current)
            continue
        if current is None or not line.startswith("Nodes ("):
            continue
        prefix, _, tail = line.partition(":")
        count_text = prefix.removeprefix("Nodes (").removesuffix(")")
        try:
            current["node_count"] = int(count_text)
        except ValueError:
            current["node_count"] = 0
        sample = tail.strip()
        if " (+" in sample:
            sample = sample.split(" (+", 1)[0]
        current["sample_nodes"] = [
            node.strip()
            for node in sample.split(",")
            if node.strip()
        ]
    return communities


def _fallback_communities(code_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not code_nodes:
        return []
    sample = [
        str(row["id"])
        for row in sorted(code_nodes, key=lambda item: str(item["id"]))[:25]
    ]
    return [
        {
            "title": "Community fixture",
            "node_count": len(code_nodes),
            "sample_nodes": sample,
        }
    ]


def _community_rows(
    root: Path,
    code_nodes: list[dict[str, Any]],
    traceability_links: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    communities = _parse_communities(_graphify_report_path(root))
    if not communities:
        communities = _fallback_communities(code_nodes)

    promoted_targets = {
        str(link["to_id"])
        for link in traceability_links
        if link.get("promoted") is True
    }
    evidence_targets = {
        str(link["to_id"])
        for link in traceability_links
        if link.get("promoted") is not True
    }
    node_lookup: dict[str, str] = {}
    for node in code_nodes:
        node_lookup[str(node["id"])] = str(node["id"])
        if node.get("label"):
            node_lookup[str(node["label"])] = str(node["id"])
        if node.get("source_file"):
            node_lookup[str(node["source_file"])] = str(node["id"])

    rows: list[dict[str, Any]] = []
    for community in communities:
        sample_ids = [
            node_lookup[sample]
            for sample in community["sample_nodes"]
            if sample in node_lookup
        ]
        rows.append(
            {
                "title": community["title"],
                "node_count": community["node_count"],
                "sample_nodes": community["sample_nodes"],
                "promoted_sample_hits": len(set(sample_ids) & promoted_targets),
                "evidence_sample_hits": len(set(sample_ids) & evidence_targets),
                "coverage_flag": (
                    "sample-uncovered-high-node-count"
                    if community["node_count"] >= 50
                    and not (set(sample_ids) & promoted_targets)
                    and not (set(sample_ids) & evidence_targets)
                    else "sample-covered-or-low-node-count"
                ),
            }
        )
    return rows


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _ascii(text: str) -> str:
    return text.encode("ascii", errors="backslashreplace").decode("ascii")


def _write_markdown(path: Path, lines: list[str]) -> None:
    path.write_text(_ascii("\n".join(lines)), encoding="utf-8")


def _sample(rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    return rows[:limit]


def _is_archived_source(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return "/archive/" in normalized or normalized.startswith("openspec/changes/archive/")


def _capability_from_stale(row: dict[str, Any]) -> str:
    from_id = str(row.get("from_id") or "")
    if from_id.startswith("openspec:"):
        parts = from_id.split(":")
        if len(parts) >= 3:
            return parts[1]
    source_path = str(row.get("source_path") or "")
    parts = source_path.replace("\\", "/").split("/")
    if "specs" in parts:
        idx = parts.index("specs")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "unclassified"


def _study_action(
    *,
    active_gaps: int,
    archived_gaps: int,
    reviewable_evidence: int,
    ambiguous_evidence: int,
    missing: dict[str, int],
) -> str:
    if active_gaps:
        missing_focus = ", ".join(
            key for key, value in sorted(missing.items()) if value
        )
        return (
            "add or promote traceability for active requirements"
            + (f" covering {missing_focus}" if missing_focus else "")
        )
    if reviewable_evidence:
        return "review evidence-only links and promote only exact, source-backed matches"
    if archived_gaps:
        return "confirm archived requirements are historical, then keep them out of active design gates"
    if ambiguous_evidence:
        return "deprioritize broad ambiguous evidence unless source context proves an exact design link"
    return "no immediate action"


def _build_study_map(
    query_outputs: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    groups: dict[str, dict[str, Any]] = {}

    def ensure(capability: str) -> dict[str, Any]:
        return groups.setdefault(
            capability,
            {
                "capability": capability,
                "active_coverage_gaps": 0,
                "archived_coverage_gaps": 0,
                "stale_evidence_links": 0,
                "reviewable_evidence_links": 0,
                "ambiguous_evidence_links": 0,
                "missing": {"implementation": 0, "test": 0, "ci": 0},
                "examples": [],
            },
        )

    for row in query_outputs.get("coverage-gaps", []):
        capability = str(row.get("capability") or "unclassified")
        group = ensure(capability)
        path = str(row.get("source_path") or "")
        if _is_archived_source(path):
            group["archived_coverage_gaps"] += 1
        else:
            group["active_coverage_gaps"] += 1
        for missing in str(row.get("missing") or "").split(","):
            missing = missing.strip()
            if missing in group["missing"]:
                group["missing"][missing] += 1
        group["examples"].append(
            {
                "kind": "coverage-gap",
                "archived": _is_archived_source(path),
                "requirement_id": row.get("requirement_id"),
                "missing": row.get("missing"),
                "source_path": row.get("source_path"),
                "source_line": row.get("source_line"),
            }
        )

    for row in query_outputs.get("stale-docs", []):
        group = ensure(_capability_from_stale(row))
        group["stale_evidence_links"] += 1
        ambiguous = row.get("provenance") == "deterministic:ambiguous-symbol"
        if ambiguous:
            group["ambiguous_evidence_links"] += 1
        else:
            group["reviewable_evidence_links"] += 1
        source_path = str(row.get("source_path") or "")
        group["examples"].append(
            {
                "kind": "ambiguous-evidence" if ambiguous else "stale-evidence",
                "archived": _is_archived_source(source_path),
                "link_kind": row.get("link_kind"),
                "witness": row.get("witness"),
                "provenance": row.get("provenance"),
                "source_path": row.get("source_path"),
                "source_line": row.get("source_line"),
            }
        )

    priorities: list[dict[str, Any]] = []
    for group in groups.values():
        score = (
            group["active_coverage_gaps"] * 1000
            + group["reviewable_evidence_links"] * 100
            + group["archived_coverage_gaps"]
            + group["ambiguous_evidence_links"]
        )
        group["priority_score"] = score
        group["recommended_action"] = _study_action(
            active_gaps=group["active_coverage_gaps"],
            archived_gaps=group["archived_coverage_gaps"],
            reviewable_evidence=group["reviewable_evidence_links"],
            ambiguous_evidence=group["ambiguous_evidence_links"],
            missing=group["missing"],
        )
        group["examples"] = sorted(
            group["examples"],
            key=lambda item: (
                bool(item.get("archived")),
                str(item.get("kind") or ""),
                str(item.get("source_path") or ""),
                int(item.get("source_line") or 0),
            ),
        )[:5]
        priorities.append(group)

    priorities.sort(
        key=lambda item: (
            -int(item["priority_score"]),
            str(item["capability"]),
        )
    )
    summary = {
        "capability_count": len(priorities),
        "active_coverage_gaps": sum(
            int(item["active_coverage_gaps"]) for item in priorities
        ),
        "archived_coverage_gaps": sum(
            int(item["archived_coverage_gaps"]) for item in priorities
        ),
        "stale_evidence_links": sum(
            int(item["stale_evidence_links"]) for item in priorities
        ),
        "reviewable_evidence_links": sum(
            int(item["reviewable_evidence_links"]) for item in priorities
        ),
        "ambiguous_evidence_links": sum(
            int(item["ambiguous_evidence_links"]) for item in priorities
        ),
        "top_priority": priorities[0]["capability"] if priorities else None,
    }
    return {
        "summary": summary,
        "priorities": priorities,
        "agent_workflow": [
            "Start with active_coverage_gaps before archived_coverage_gaps.",
            "Inspect each example source_path/source_line before changing code.",
            "Promote evidence-only links only when exact identifiers, paths, or reviewed design evidence support them.",
            "For archived-only gaps, prefer documenting historical status over implementing stale requirements.",
        ],
    }


def _write_study_map(out_dir: Path, *, study_map: dict[str, Any]) -> None:
    (out_dir / "study-map.json").write_text(
        _json_dumps(study_map),
        encoding="utf-8",
    )

    summary = study_map["summary"]
    lines = [
        "# AI study map",
        "",
        "This file turns raw design-KG query results into a prioritized map for",
        "agents that need to improve design, utility, or traceability.",
        "",
        "## Summary",
        "",
        f"- capabilities with work: {summary['capability_count']}",
        f"- active coverage gaps: {summary['active_coverage_gaps']}",
        f"- archived coverage gaps: {summary['archived_coverage_gaps']}",
        f"- stale evidence links: {summary['stale_evidence_links']}",
        f"- reviewable evidence links: {summary['reviewable_evidence_links']}",
        f"- ambiguous evidence links: {summary['ambiguous_evidence_links']}",
        f"- top priority: {summary['top_priority'] or 'none'}",
        "",
        "## Agent Workflow",
        "",
    ]
    for step in study_map["agent_workflow"]:
        lines.append(f"- {step}")
    lines.extend(["", "## Priorities", ""])
    if not study_map["priorities"]:
        lines.extend(["No priority rows.", ""])
    for row in study_map["priorities"]:
        lines.extend(
            [
                f"### {row['capability']}",
                "",
                f"- priority score: {row['priority_score']}",
                f"- active coverage gaps: {row['active_coverage_gaps']}",
                f"- archived coverage gaps: {row['archived_coverage_gaps']}",
                f"- stale evidence links: {row['stale_evidence_links']}",
                f"- reviewable evidence links: {row['reviewable_evidence_links']}",
                f"- ambiguous evidence links: {row['ambiguous_evidence_links']}",
                f"- missing implementation/test/ci: "
                f"{row['missing']['implementation']}/"
                f"{row['missing']['test']}/"
                f"{row['missing']['ci']}",
                f"- recommended action: {row['recommended_action']}",
                "",
            ]
        )
        for example in row["examples"]:
            lines.append(
                "- example: "
                f"{example.get('kind')} "
                f"{example.get('source_path')}:{example.get('source_line')}"
            )
        lines.append("")
    _write_markdown(out_dir / "study-map.md", lines)


def _write_readme(
    out_dir: Path,
    *,
    metadata: dict[str, Any],
    counts: dict[str, int],
) -> None:
    lines = [
        "# Design-intelligence KG audit",
        "",
        f"- date: {metadata['date']}",
        f"- commit: {metadata['commit']}",
        f"- graphify version: {metadata['graphify_version']}",
        f"- graphify graph: {metadata['graphify_graph']}",
        "",
        "## Counts",
        "",
    ]
    for key, value in counts.items():
        lines.append(f"- {key.replace('_', ' ')}: {value}")
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
        ]
    )
    for command in metadata["projection_commands"]:
        lines.append(f"- `{command}`")
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `snapshot-summary.json`: machine-readable counts and query sizes.",
            "- `coverage-map.md`: graphify community samples and trace hits.",
            "- `findings.md`: coverage gaps, stale evidence, and test gaps.",
            "- `queries.md`: reproducible named query samples with provenance.",
            "- `study-map.json` / `study-map.md`: AI-facing priority map.",
            "- `review-gate.md`: Phase 6 compliance and code-quality review.",
            "",
        ]
    )
    _write_markdown(out_dir / "README.md", lines)


def _write_coverage_map(
    out_dir: Path,
    *,
    communities: list[dict[str, Any]],
) -> None:
    lines = [
        "# Graphify community coverage",
        "",
        "This report maps graphify community samples to promoted and evidence-only",
        "design traceability targets. Graphify reports only sample nodes for large",
        "communities, so hit counts are conservative.",
        "",
    ]
    for row in communities:
        sample = ", ".join(row["sample_nodes"]) if row["sample_nodes"] else "none"
        lines.extend(
            [
                f"## {row['title']}",
                "",
                f"- nodes: {row['node_count']}",
                f"- coverage flag: {row['coverage_flag']}",
                f"- promoted sample hits: {row['promoted_sample_hits']}",
                f"- evidence-only sample hits: {row['evidence_sample_hits']}",
                f"- sample: {sample}",
                "",
            ]
        )
    _write_markdown(out_dir / "coverage-map.md", lines)


def _write_findings(
    out_dir: Path,
    *,
    query_outputs: dict[str, list[dict[str, Any]]],
    counts: dict[str, int],
) -> None:
    lines = [
        "# Design KG findings",
        "",
        "## Important findings",
        "",
        (
            f"- coverage-gaps: {len(query_outputs['coverage-gaps'])} requirements "
            "lack at least one promoted implementation, test, or CI link."
        ),
        (
            f"- stale-docs: {len(query_outputs['stale-docs'])} evidence-only "
            "links need review before promotion."
        ),
        (
            f"- untested-god-nodes: {len(query_outputs['untested-god-nodes'])} "
            "high-rank graphify nodes lack promoted test links."
        ),
        (
            f"- promoted traceability links: {counts['promoted_links']} of "
            f"{counts['traceability_links']} total traceability links."
        ),
        "",
    ]
    for name in ("coverage-gaps", "stale-docs", "untested-god-nodes"):
        rows = query_outputs[name]
        lines.extend([f"## {name}", "", f"Total rows: {len(rows)}", ""])
        if not rows:
            lines.extend(["No rows.", ""])
            continue
        for row in _sample(rows):
            lines.append(f"- `{row.get('source_path')}:{row.get('source_line')}`")
            lines.append(f"  `{json.dumps(row, ensure_ascii=True, sort_keys=True)}`")
        if len(rows) > 20:
            lines.append(f"- omitted rows: {len(rows) - 20}")
        lines.append("")
    _write_markdown(out_dir / "findings.md", lines)


def _write_queries(
    out_dir: Path,
    *,
    query_outputs: dict[str, list[dict[str, Any]]],
) -> None:
    lines = [
        "# Named design KG query samples",
        "",
        "Every row keeps `source_path` and `source_line` so an agent can inspect",
        "the backing evidence before proposing a design change.",
        "",
    ]
    for name in QUERY_NAMES:
        rows = query_outputs.get(name, [])
        lines.extend([f"## {name}", "", f"Rows: {len(rows)}", ""])
        if not rows:
            lines.extend(["No rows.", ""])
            continue
        for row in _sample(rows):
            lines.append(
                f"- `{json.dumps(row, ensure_ascii=True, sort_keys=True)}`"
            )
        if len(rows) > 20:
            lines.append(f"- omitted rows: {len(rows) - 20}")
        lines.append("")
    _write_markdown(out_dir / "queries.md", lines)


def build_design_kg_audit(
    *,
    root: Path,
    out_dir: Path,
    date: str | None = None,
    commit: str | None = None,
    graphify_version: str | None = None,
) -> dict[str, Any]:
    """Project the design KG and write deterministic audit artifacts."""
    root = Path(root).resolve()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    store = _build_store(root)
    rows = {name: _relation(store, name) for name in RELATION_COLUMNS}
    traceability_links = rows["traceability_link"]
    promoted_links = [
        link for link in traceability_links if link.get("promoted") is True
    ]
    evidence_only_links = [
        link for link in traceability_links if link.get("promoted") is not True
    ]
    counts = {
        "requirements": len(rows["design_requirement"]),
        "design_scenarios": len(rows["design_scenario"]),
        "design_decisions": len(rows["design_decision"]),
        "operator_commands": len(rows["operator_command"]),
        "tests": len(rows["test_case"]),
        "ci_workflows": len(rows["ci_workflow"]),
        "ci_jobs": len(rows["ci_job"]),
        "traceability_links": len(traceability_links),
        "promoted_links": len(promoted_links),
        "evidence_only_links": len(evidence_only_links),
        "graph_nodes": len(rows["code_node"]),
        "graph_edges": len(rows["code_edge"]),
    }
    query_outputs = _query_outputs(store, rows)
    communities = _community_rows(root, rows["code_node"], traceability_links)

    graph_path = _graphify_path(root)
    report_paths = {
        "readme": "README.md",
        "summary": "snapshot-summary.json",
        "coverage_map": "coverage-map.md",
        "findings": "findings.md",
        "queries": "queries.md",
        "study_map": "study-map.md",
        "study_map_json": "study-map.json",
        "review_gate": "review-gate.md",
    }
    metadata = {
        "date": date or date_type.today().isoformat(),
        "commit": commit or _detect_commit(root),
        "graphify_version": graphify_version or _detect_graphify_version(root),
        "graphify_graph": _rel(graph_path, root) if graph_path else "missing",
        "projection_commands": [
            "python -m graphify update . --no-cluster --force",
            "python -m graphify cluster-only . --no-viz --no-label",
            (
                "python skills/book-knowledge/scripts/build_design_kg_audit.py "
                "--root . --out docs/audits/<date>-design-intelligence-kg "
                "--date <date>"
            ),
        ],
        "report_paths": report_paths,
        "schema": _rel(SCHEMA_PATH, root),
    }
    summary = {
        "metadata": metadata,
        "counts": counts,
        "query_counts": {
            name: len(output)
            for name, output in sorted(query_outputs.items())
        },
    }

    (out_dir / "snapshot-summary.json").write_text(
        _json_dumps(summary),
        encoding="utf-8",
    )
    _write_readme(out_dir, metadata=metadata, counts=counts)
    _write_coverage_map(out_dir, communities=communities)
    _write_findings(out_dir, query_outputs=query_outputs, counts=counts)
    _write_queries(out_dir, query_outputs=query_outputs)
    _write_study_map(out_dir, study_map=_build_study_map(query_outputs))

    return {
        "artifact_dir": str(out_dir),
        "requirements": counts["requirements"],
        "design_decisions": counts["design_decisions"],
        "tests": counts["tests"],
        "ci_workflows": counts["ci_workflows"],
        "ci_jobs": counts["ci_jobs"],
        "traceability_links": counts["traceability_links"],
        "promoted_links": counts["promoted_links"],
        "evidence_only_links": counts["evidence_only_links"],
        "graph_nodes": counts["graph_nodes"],
        "graph_edges": counts["graph_edges"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a design-intelligence KG audit artifact.",
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--date")
    parser.add_argument("--commit")
    parser.add_argument("--graphify-version")
    args = parser.parse_args(argv)

    result = build_design_kg_audit(
        root=args.root,
        out_dir=args.out,
        date=args.date,
        commit=args.commit,
        graphify_version=args.graphify_version,
    )
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
