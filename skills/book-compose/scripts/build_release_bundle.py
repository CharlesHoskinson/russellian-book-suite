"""Assemble a chapter release bundle (Markdown always; Pandoc-derived formats if Pandoc is on PATH).

Workspace-level style overrides
-------------------------------
If `<workspace>/style-overrides.json` exists, `chapter_contract_check.check_draft`
exposes it to russellian-style via the `RUSSELLIAN_OVERRIDES` env var. The path
constant lives in `scripts.sibling_skills.workspace_style_overrides_path`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .evidence_summary import build_evidence_summary
from .sibling_skills import load_book_knowledge_module

ASSETS = Path(__file__).resolve().parent.parent / "assets"
PANDOC = ASSETS / "pandoc"


def _workspace_conformance(workspace: Path) -> tuple[bool, bool]:
    """Compute (shacl_conforms, competency_clean) for the current workspace graph.

    Mirrors book_preflight's workspace audit so the bundle manifest records the
    chapter's real conformance state at build time rather than a hardcoded True.
    """
    workspace_mod = load_book_knowledge_module("workspace")
    validate_shacl_mod = load_book_knowledge_module("validate_shacl")
    queries_mod = load_book_knowledge_module("run_competency_queries")
    layout = workspace_mod.WorkspaceLayout(Path(workspace))
    shacl = validate_shacl_mod.validate_shacl(layout)
    queries = queries_mod.run_competency_queries(layout)
    competency_clean = (
        len(queries.get("unsupported_claims", [])) == 0
        and len(queries.get("contradiction_scan", [])) == 0
    )
    return bool(shacl.conforms), competency_clean


def _claim_slice(workspace: Path, chapter_id: str) -> tuple[list[dict], list[str]]:
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")
    layout = workspace_mod.WorkspaceLayout(workspace)
    latest: dict[str, dict] = {}
    for r in ledger_mod.read_claims(layout):
        latest[r["claim_id"]] = r
    sliced = [c for c in latest.values()
              if c["status"] == "verified" and chapter_id in c.get("supports_chapters", [])]
    sources = sorted({s["doc_id"] for c in sliced for s in c["source_spans"]})
    return sliced, sources


def _run_pandoc(input_md: Path, out: Path, fmt: str) -> bool:
    args = ["pandoc", str(input_md), "-o", str(out), "--standalone"]
    if fmt == "pdf":
        args += ["--pdf-engine=xelatex", "--template", str(PANDOC / "manuscript.tex")]
    elif fmt == "epub":
        args += ["-t", "epub3"]
    elif fmt == "latex":
        args += ["-t", "latex", "--template", str(PANDOC / "manuscript.tex")]
    try:
        subprocess.run(args, check=True, capture_output=True, text=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def build_release_bundle(workspace: Path, chapter_id: str, version: str,
                         formats: list[str]) -> Path:
    workspace = Path(workspace).resolve()
    drafts_dir = workspace / "chapters" / "drafts" / chapter_id
    draft_md = drafts_dir / "draft.md"
    if not draft_md.is_file():
        raise FileNotFoundError(f"no draft at {draft_md}")

    bundle = workspace / "chapters" / "releases" / f"{chapter_id}-{version}"
    bundle.mkdir(parents=True, exist_ok=True)

    shutil.copy(draft_md, bundle / "draft.md")

    evidence = build_evidence_summary(workspace, chapter_id)
    (bundle / "evidence-summary.md").write_text(evidence, encoding="utf-8")

    sliced, sources = _claim_slice(workspace, chapter_id)
    with (bundle / "claims-slice.jsonl").open("w", encoding="utf-8") as fh:
        for c in sliced:
            fh.write(json.dumps(c, sort_keys=True) + "\n")

    outputs = ["draft.md"]
    for fmt in formats:
        if fmt == "markdown":
            continue
        ext = {"pdf": "pdf", "epub": "epub", "latex": "tex"}.get(fmt)
        if ext is None:
            continue
        out = bundle / f"draft.{ext}"
        if _run_pandoc(draft_md, out, fmt):
            outputs.append(f"draft.{ext}")

    shacl_conforms, competency_clean = _workspace_conformance(workspace)
    manifest = {
        "chapter_id": chapter_id,
        "version": version,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "outputs": outputs,
        "sources_included": sources,
        "claim_slice_count": len(sliced),
        "shacl_conforms": shacl_conforms,
        "competency_clean": competency_clean,
    }
    (bundle / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")

    return bundle
