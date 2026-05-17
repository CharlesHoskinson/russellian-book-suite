"""
Public API surface of book-knowledge (IF-BK-1..4).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

API_VERSION = (0, 1)

__all__ = [
    "IngestResult",
    "ClaimRecord",
    "ClaimFilter",
    "ConceptRef",
    "ingest_pdf",
    "query_claims",
    "is_source_ingested",
    "list_concepts",
]

# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------

@dataclass
class IngestResult:
    source_id: str
    sha256: str
    claims_extracted: int
    wiki_pages_touched: list[str]
    status: Literal["ingested", "already_present", "failed"]


@dataclass
class ClaimRecord:
    id: str
    state: Literal["proposed", "verified", "disputed", "superseded"]
    tags: list[str]
    source_id: str
    body: str
    locator: str


@dataclass
class ClaimFilter:
    tags: Optional[list[str]] = None
    topics: Optional[list[str]] = None
    source_ids: Optional[list[str]] = None
    state: Optional[Literal["proposed", "verified", "disputed", "superseded"]] = None


@dataclass
class ConceptRef:
    slug: str
    title: str
    sources: list[str]
    surface_forms: list[str]


# ---------------------------------------------------------------------------
# Lazy script imports (avoid import errors when scripts/ deps missing)
# ---------------------------------------------------------------------------

def _scripts_path(workspace_root: Path) -> None:
    """Insert the skill root into sys.path so `scripts` is importable."""
    skill_root = Path(__file__).resolve().parent
    if str(skill_root) not in sys.path:
        sys.path.insert(0, str(skill_root))


def _get_layout(workspace_root: Path):
    from scripts.workspace import WorkspaceLayout
    return WorkspaceLayout(workspace_root)


# ---------------------------------------------------------------------------
# IF-BK-1: ingest_pdf
# ---------------------------------------------------------------------------

def ingest_pdf(source_path: Path, workspace_root: Path) -> IngestResult:
    """Ingest a PDF into the workspace.  Returns IngestResult with status
    'ingested', 'already_present', or 'failed'."""
    _scripts_path(workspace_root)
    from scripts.source_manifest import compute_sha256, load_manifest
    from scripts.workspace import WorkspaceLayout, init_workspace

    src = Path(source_path).resolve()
    ws = Path(workspace_root)

    # Compute sha256 first for duplicate check
    try:
        sha = compute_sha256(src)
    except Exception:
        return IngestResult(
            source_id="",
            sha256="",
            claims_extracted=0,
            wiki_pages_touched=[],
            status="failed",
        )

    layout = WorkspaceLayout(ws)

    # Check if already ingested by looking for an existing manifest with this sha256
    if layout.manifests.is_dir():
        for manifest_path in layout.manifests.glob("*.json"):
            try:
                m = load_manifest(manifest_path)
                if m.get("sha256") == sha:
                    from scripts.source_manifest import compute_doc_id
                    doc_id = m.get("doc_id") or compute_doc_id(src.name)
                    return IngestResult(
                        source_id=doc_id,
                        sha256=sha,
                        claims_extracted=0,
                        wiki_pages_touched=[],
                        status="already_present",
                    )
            except Exception:
                continue

    # Perform the actual ingest
    try:
        from scripts.ingest_pdf import ingest_pdf as _ingest_pdf
        manifest = _ingest_pdf(src, ws)
        doc_id = manifest["doc_id"]

        # Collect wiki pages touched
        touched: list[str] = []
        source_page = layout.wiki_sources / f"{doc_id}.md"
        if source_page.exists():
            touched.append(str(source_page.relative_to(ws)))

        return IngestResult(
            source_id=doc_id,
            sha256=sha,
            claims_extracted=0,
            wiki_pages_touched=touched,
            status="ingested",
        )
    except Exception:
        return IngestResult(
            source_id="",
            sha256=sha,
            claims_extracted=0,
            wiki_pages_touched=[],
            status="failed",
        )


# ---------------------------------------------------------------------------
# IF-BK-2: query_claims
# ---------------------------------------------------------------------------

def query_claims(filter_: ClaimFilter, workspace_root: Path) -> list[ClaimRecord]:
    """Return claims matching the given filter."""
    _scripts_path(workspace_root)
    from scripts.ledger import read_claims
    from scripts.io_utils import latest_per

    layout = _get_layout(Path(workspace_root))
    raw = list(latest_per(read_claims(layout), "claim_id").values())

    results: list[ClaimRecord] = []
    for rec in raw:
        # Map claim state — skip states outside the public API set
        state = rec.get("status", "proposed")
        if state not in ("proposed", "verified", "disputed", "superseded"):
            continue

        # Derive tags from semantic_class if present
        sc = rec.get("semantic_class")
        tags: list[str] = [sc] if sc else []

        # Derive source_id and locator from first source_span
        spans = rec.get("source_spans") or []
        source_id = spans[0]["doc_id"] if spans else ""
        locator = spans[0].get("locator_text", "") if spans else ""

        record = ClaimRecord(
            id=rec["claim_id"],
            state=state,
            tags=tags,
            source_id=source_id,
            body=rec.get("canonical_text", ""),
            locator=locator,
        )

        # Apply filters
        if filter_.state is not None and record.state != filter_.state:
            continue
        if filter_.source_ids is not None and record.source_id not in filter_.source_ids:
            continue
        if filter_.tags is not None:
            if not any(t in record.tags for t in filter_.tags):
                continue
        if filter_.topics is not None:
            # topics filter: match against canonical_text or tags (best-effort)
            body_lower = record.body.lower()
            if not any(topic.lower() in body_lower for topic in filter_.topics):
                continue

        results.append(record)

    return results


# ---------------------------------------------------------------------------
# IF-BK-3: is_source_ingested
# ---------------------------------------------------------------------------

def is_source_ingested(sha256: str, workspace_root: Path) -> bool:
    """Return True if a source with the given sha256 has been ingested."""
    _scripts_path(workspace_root)
    from scripts.source_manifest import load_manifest

    layout = _get_layout(Path(workspace_root))
    if not layout.manifests.is_dir():
        return False

    for manifest_path in layout.manifests.glob("*.json"):
        try:
            m = load_manifest(manifest_path)
            if m.get("sha256") == sha256:
                return True
        except Exception:
            continue
    return False


# ---------------------------------------------------------------------------
# IF-BK-4: list_concepts
# ---------------------------------------------------------------------------

def _parse_yaml_frontmatter(text: str) -> tuple[dict, str]:
    """Parse optional YAML frontmatter from a markdown file.

    Returns (frontmatter_dict, body_text).  If no frontmatter, returns
    ({}, original text).
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    fm_text = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1:])
    try:
        import yaml
        fm = yaml.safe_load(fm_text) or {}
    except Exception:
        fm = {}
    return fm, body


def list_concepts(workspace_root: Path) -> list[ConceptRef]:
    """Return ConceptRef for every concept page in wiki/concepts/."""
    layout = _get_layout(Path(workspace_root))
    concepts_dir = layout.wiki_concepts
    if not concepts_dir.is_dir():
        return []

    results: list[ConceptRef] = []
    for md_file in sorted(concepts_dir.glob("*.md")):
        slug = md_file.stem
        text = md_file.read_text(encoding="utf-8")
        fm, _body = _parse_yaml_frontmatter(text)

        title = fm.get("title") or slug
        sources = fm.get("sources") or []
        surface_forms = fm.get("surface_forms") or []

        if isinstance(sources, str):
            sources = [sources]
        if isinstance(surface_forms, str):
            surface_forms = [surface_forms]

        results.append(ConceptRef(
            slug=slug,
            title=title,
            sources=list(sources),
            surface_forms=list(surface_forms),
        ))

    return results
