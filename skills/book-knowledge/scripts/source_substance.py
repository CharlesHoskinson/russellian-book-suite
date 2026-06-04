"""Flag claims backed by a thin source.

``verify_claim`` confirms a locator phrase is *present* in its source; it does not
confirm the source has substance. A captured page that is nothing but YAML
frontmatter can still carry the locator in its title and pass verification, which is
how a stub once slipped through as if it were the underlying paper. This guard
measures the source body (frontmatter stripped) and flags any claim whose source
falls below a minimum. It warns rather than fails: a genuinely short source should
be surfaced for a human to judge, not silently blocked.
"""
from __future__ import annotations

import re

from .ledger import read_claims
from .source_manifest import load_manifest
from .workspace import WorkspaceLayout

MIN_SOURCE_BODY_CHARS = 250

_FRONTMATTER = re.compile(r"\A\s*---\s*\n.*?\n---\s*\n", re.DOTALL)


def source_body(text: str) -> str:
    """Return the source text with a single leading YAML frontmatter block removed."""
    return _FRONTMATTER.sub("", text, count=1).strip()


def body_chars(text: str) -> int:
    return len(source_body(text))


def _current_claims(layout: WorkspaceLayout) -> dict:
    """Collapse the append-only ledger to one tip record per claim id."""
    tips: dict = {}
    for record in read_claims(layout):
        tips[record["claim_id"]] = record
    return tips


def find_thin_sourced_claims(layout: WorkspaceLayout,
                             min_body_chars: int = MIN_SOURCE_BODY_CHARS) -> list[dict]:
    """Return one entry per (claim, span) whose source is too thin to be evidence.

    Markdown sources are measured by body characters (frontmatter stripped). A PDF
    with at least one page is treated as substantial without re-extracting it; a
    zero-page PDF is flagged. Superseded and refuted claims are skipped.
    """
    flagged: list[dict] = []
    for cid, claim in _current_claims(layout).items():
        if claim.get("status") in ("superseded", "refuted"):
            continue
        for span in claim["source_spans"]:
            doc_id = span["doc_id"]
            manifest_path = layout.manifests / f"{doc_id}.json"
            if not manifest_path.exists():
                flagged.append({"claim_id": cid, "doc_id": doc_id,
                                "body_chars": None, "reason": "no manifest"})
                continue
            manifest = load_manifest(manifest_path)
            kind = manifest.get("source_kind")
            if kind == "pdf":
                if (manifest.get("page_count") or 0) > 0:
                    continue
                flagged.append({"claim_id": cid, "doc_id": doc_id,
                                "body_chars": 0, "reason": "zero-page pdf"})
            elif kind == "markdown":
                raw = (layout.raw_markdown / manifest["doc_name"]).read_text(encoding="utf-8")
                n = body_chars(raw)
                if n < min_body_chars:
                    flagged.append({"claim_id": cid, "doc_id": doc_id,
                                    "body_chars": n, "reason": "thin source body"})
    return flagged
