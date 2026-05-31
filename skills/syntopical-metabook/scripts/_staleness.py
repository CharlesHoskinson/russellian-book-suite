"""Refuse to render from an artifact older than its source ledgers."""
from __future__ import annotations
from pathlib import Path


class StaleArtifactError(RuntimeError):
    """Raised when a generated artifact is older than a source it derives from."""


def check_not_stale(artifact: Path, sources: list[Path]) -> None:
    """Raise StaleArtifactError if `artifact` is missing or older than any
    existing path in `sources`. Missing sources are ignored."""
    artifact = Path(artifact)
    if not artifact.exists():
        raise StaleArtifactError(
            f"{artifact} does not exist. Run `forge govern build` first."
        )
    art_mtime = artifact.stat().st_mtime
    for src in sources:
        src = Path(src)
        if src.exists() and src.stat().st_mtime > art_mtime:
            raise StaleArtifactError(
                f"{artifact.name} is stale relative to {src.name}; "
                f"run `forge govern build` first."
            )
