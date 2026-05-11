"""Pre-flight gate for book-level release.

Verifies that every chapter contract has a matching release directory at the
expected version, that each release manifest validates, and that the
workspace's SHACL graph still conforms.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import yaml

from .chapter_contract import load_contract, ContractValidationError
from .sibling_skills import load_book_knowledge_module

ASSETS = Path(__file__).resolve().parent.parent / "assets"
RELEASE_SCHEMA = json.loads((ASSETS / "release-manifest.schema.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class BookPreflightResult:
    passes: bool
    chapter_count: int
    missing_releases: list[str]
    failed_contracts: list[str]
    shacl_conforms: bool
    unsupported_claims: int
    contradictions: int
    report_path: Path
    issues: list[str] = field(default_factory=list)


def _enumerate_contracts(workspace: Path) -> list[str]:
    contracts_dir = Path(workspace) / "chapters" / "contracts"
    if not contracts_dir.is_dir():
        return []
    chapter_ids: list[str] = []
    for path in sorted(contracts_dir.glob("ch-*.yaml")):
        try:
            c = load_contract(path)
            chapter_ids.append(c["chapter_id"])
        except ContractValidationError:
            chapter_ids.append(f"INVALID:{path.stem}")
    return chapter_ids


def _check_chapter_release(workspace: Path, chapter_id: str, version: str) -> tuple[bool, str]:
    release_dir = Path(workspace) / "chapters" / "releases" / f"{chapter_id}-{version}"
    manifest_path = release_dir / "manifest.yaml"
    if not manifest_path.is_file():
        return False, f"release dir missing: {release_dir.name}"
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        jsonschema.validate(manifest, RELEASE_SCHEMA)
    except (jsonschema.ValidationError, yaml.YAMLError) as e:
        return False, f"manifest invalid for {chapter_id}: {e}"
    return True, ""


def _run_workspace_audit(workspace: Path) -> tuple[bool, int, int]:
    workspace_mod = load_book_knowledge_module("workspace")
    validate_shacl_mod = load_book_knowledge_module("validate_shacl")
    queries_mod = load_book_knowledge_module("run_competency_queries")
    layout = workspace_mod.WorkspaceLayout(Path(workspace))
    shacl = validate_shacl_mod.validate_shacl(layout)
    queries = queries_mod.run_competency_queries(layout)
    return (
        shacl.conforms,
        len(queries.get("unsupported_claims", [])),
        len(queries.get("contradiction_scan", [])),
    )


def book_preflight(workspace: Path, chapter_versions: dict[str, str]) -> BookPreflightResult:
    workspace = Path(workspace).resolve()
    if not (workspace / "CLAUDE.md").is_file():
        raise FileNotFoundError(f"not a book-knowledge workspace: {workspace}")

    expected_chapters = _enumerate_contracts(workspace)
    missing: list[str] = []
    failed_contracts: list[str] = []
    issues: list[str] = []

    for chapter_id in expected_chapters:
        if chapter_id.startswith("INVALID:"):
            failed_contracts.append(chapter_id.removeprefix("INVALID:"))
            issues.append(f"contract failed to validate: {chapter_id}")
            continue
        version = chapter_versions.get(chapter_id)
        if version is None:
            missing.append(chapter_id)
            issues.append(f"no version provided for {chapter_id}")
            continue
        ok, msg = _check_chapter_release(workspace, chapter_id, version)
        if not ok:
            missing.append(chapter_id)
            issues.append(msg)

    shacl_conforms, unsupported, contradictions = _run_workspace_audit(workspace)
    if not shacl_conforms:
        issues.append("SHACL non-conforming")
    if unsupported:
        issues.append(f"{unsupported} unsupported verified claims")
    if contradictions:
        issues.append(f"{contradictions} contradiction pairs")

    passes = (
        not missing and not failed_contracts and shacl_conforms
        and unsupported == 0 and contradictions == 0
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    preflight_dir = workspace / "book" / "preflight"
    preflight_dir.mkdir(parents=True, exist_ok=True)
    report_path = preflight_dir / f"book-preflight-{timestamp}.md"
    lines = [
        f"# Book Preflight Report - {timestamp}",
        "",
        f"- passes: {passes}",
        f"- chapter_count: {len(expected_chapters)}",
        f"- missing_releases: {missing or '(none)'}",
        f"- failed_contracts: {failed_contracts or '(none)'}",
        f"- shacl_conforms: {shacl_conforms}",
        f"- unsupported_claims: {unsupported}",
        f"- contradictions: {contradictions}",
        "",
    ]
    if issues:
        lines.append("## Issues")
        for i in issues:
            lines.append(f"- {i}")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    return BookPreflightResult(
        passes=passes,
        chapter_count=len(expected_chapters),
        missing_releases=missing,
        failed_contracts=failed_contracts,
        shacl_conforms=shacl_conforms,
        unsupported_claims=unsupported,
        contradictions=contradictions,
        report_path=report_path,
        issues=issues,
    )
