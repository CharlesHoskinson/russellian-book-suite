"""REQ-CORPUS-043, 044: build-log shape and profile link discipline."""
from __future__ import annotations

import re
from pathlib import Path


def _build_log(repo_root: Path) -> Path:
    return repo_root / "docs" / "eval" / "2026-05-19-scale-corpus-build-log.md"


REQUIRED_FIELDS = (
    "When encountered",
    "What broke",
    "Tier closing this gap",
    "Workaround used",
    "Status",
)


def test_build_log_has_entries_with_required_fields(repo_root: Path) -> None:
    log = _build_log(repo_root)
    assert log.exists(), f"missing build log: {log}"
    text = log.read_text(encoding="utf-8")

    # Each entry must be a `## Gap: ...` block.
    entries = re.split(r"^##\s+Gap:\s+", text, flags=re.MULTILINE)
    # First element is the preamble; the rest are entries.
    gaps = entries[1:]
    assert len(gaps) >= 3, f"need >= 3 gap entries, got {len(gaps)}"

    for i, body in enumerate(gaps, start=1):
        for field in REQUIRED_FIELDS:
            assert field in body, (
                f"gap entry #{i} missing required field {field!r}; "
                f"body head: {body[:200]!r}"
            )


def test_slow_phases_link_profile_artefacts(repo_root: Path) -> None:
    """If the build log notes a >5min phase, it must link a profile artefact
    under docs/eval/profiles/."""
    log = _build_log(repo_root)
    text = log.read_text(encoding="utf-8")
    # If there's a "Slow phase" / ">5 min" mention without a profile link,
    # fail. Otherwise (no slow phase declared, or slow phase with profile),
    # pass.
    slow_pattern = re.compile(
        r"(?im)(?:slow\s+phase|>\s*5\s*min|over\s+5\s+min)"
    )
    profile_pattern = re.compile(r"docs/eval/profiles/")
    if slow_pattern.search(text):
        assert profile_pattern.search(text), (
            "build log mentions a slow phase but links no docs/eval/profiles/ artefact"
        )
