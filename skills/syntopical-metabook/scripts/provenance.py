"""Provenance footer helpers for syntopical-metabook artifact writers (NFR-8).

All artifact files written by this skill append a stable footer that identifies
the generating code without a timestamp.  Omitting the timestamp keeps the
footer deterministic so idempotence (REQ-SYN-4) is preserved: running the
writers twice on the same inputs produces byte-identical output.

Footer format (Markdown sub-element):

    ---
    <sub>generated_by: syntopical-metabook v0.1.0 · source_run_id: <id> ·
    skill_api_versions: {book-knowledge: 0.1, booklogic: 0.0.0-stub}</sub>
"""
from __future__ import annotations

_SKILL_VERSION = "v0.1.0"
_BK_API_VERSION = "0.1"
_BOOKLOGIC_VERSION = "0.0.0-stub"


def provenance_footer(source_run_id: str = "") -> str:
    """Return a stable Markdown provenance footer block.

    The footer contains no timestamp so repeated identical runs produce the
    same file contents (preserving REQ-SYN-4 idempotence).
    """
    rid = source_run_id or "unspecified"
    return (
        "\n---\n"
        f"<sub>generated_by: syntopical-metabook {_SKILL_VERSION} · "
        f"source_run_id: {rid} · "
        f"skill_api_versions: {{book-knowledge: {_BK_API_VERSION}, "
        f"booklogic: {_BOOKLOGIC_VERSION}}}</sub>\n"
    )
