"""Pre-flight gate for chapter compilation.

Imports book-knowledge's validate_shacl compatibility contract and
run_competency_queries via the sibling-skills loader. Both execute over the
EDN/Cozo path in the book-knowledge venv.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .sibling_skills import load_book_knowledge_module


@dataclass(frozen=True)
class PreflightResult:
    passes: bool
    shacl_conforms: bool
    unsupported_claims: int
    contradictions: int
    report_path: Path
    issues: list[str] = field(default_factory=list)


def preflight(workspace: Path) -> PreflightResult:
    workspace = Path(workspace).resolve()
    if not workspace.is_dir() or not (workspace / "CLAUDE.md").is_file():
        raise FileNotFoundError(f"not a book-knowledge workspace: {workspace}")

    workspace_mod = load_book_knowledge_module("workspace")
    validate_shacl_mod = load_book_knowledge_module("validate_shacl")
    queries_mod = load_book_knowledge_module("run_competency_queries")

    layout = workspace_mod.WorkspaceLayout(workspace)
    shacl = validate_shacl_mod.validate_shacl(layout)
    queries = queries_mod.run_competency_queries(layout)

    unsupported = len(queries.get("unsupported_claims", []))
    contradictions = len(queries.get("contradiction_scan", []))
    passes = shacl.conforms and unsupported == 0 and contradictions == 0

    issues: list[str] = []
    if not shacl.conforms:
        issues.append(f"SHACL non-conforming: {len(shacl.violations)} violations")
    if unsupported:
        issues.append(f"{unsupported} verified claims missing provenance")
    if contradictions:
        issues.append(f"{contradictions} contradiction pairs")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = layout.graph_reports / f"preflight-{timestamp}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Preflight Report — {timestamp}",
        "",
        f"- passes: {passes}",
        f"- shacl_conforms: {shacl.conforms}",
        f"- unsupported_claims: {unsupported}",
        f"- contradictions: {contradictions}",
        "",
    ]
    if issues:
        lines.append("## Issues")
        for i in issues:
            lines.append(f"- {i}")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    return PreflightResult(
        passes=passes,
        shacl_conforms=shacl.conforms,
        unsupported_claims=unsupported,
        contradictions=contradictions,
        report_path=report_path,
        issues=issues,
    )
