"""REQ-CORPUS-045: cross-paragraph corpus-scope constraint or logged gap."""
from __future__ import annotations

from pathlib import Path


def test_at_least_one_scope_corpus_constraint_or_logged_gap(
    project_root: Path, repo_root: Path
) -> None:
    constraints = (
        project_root / "rules" / "booklogic" / "constraints.edn"
    ).read_text(encoding="utf-8")
    has_corpus_scope = ":scope :corpus" in constraints or ":scope:corpus" in constraints
    if has_corpus_scope:
        return

    # No corpus-scope constraint → the build log MUST log this gap and link
    # tier5-cross-chapter (Phase R).
    log = (
        repo_root / "docs" / "eval" / "2026-05-19-scale-corpus-build-log.md"
    ).read_text(encoding="utf-8")
    assert ":scope :corpus" in log or "scope :corpus" in log or "scope corpus" in log, (
        "constraints.edn has no :scope :corpus AND build log does not document the gap"
    )
    assert "tier5-cross-chapter" in log, (
        "build log must link tier5-cross-chapter (Phase R) for the deferred constraint"
    )
