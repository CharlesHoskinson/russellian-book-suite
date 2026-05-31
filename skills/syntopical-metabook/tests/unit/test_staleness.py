"""Staleness guard: positions.edn must be newer than its source ledgers."""
from __future__ import annotations
import os
import pytest
from scripts._staleness import StaleArtifactError, check_not_stale


def _touch(path, mtime):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_passes_when_artifact_newer(tmp_path):
    src = tmp_path / "ledger.jsonl"
    art = tmp_path / "positions.edn"
    _touch(src, 1000)
    _touch(art, 2000)
    check_not_stale(art, [src])  # no raise


def test_raises_when_artifact_older(tmp_path):
    src = tmp_path / "ledger.jsonl"
    art = tmp_path / "positions.edn"
    _touch(src, 2000)
    _touch(art, 1000)
    with pytest.raises(StaleArtifactError, match="run `forge govern build`"):
        check_not_stale(art, [src])


def test_missing_sources_are_ignored(tmp_path):
    art = tmp_path / "positions.edn"
    _touch(art, 1000)
    check_not_stale(art, [tmp_path / "absent.jsonl"])  # no raise


def test_missing_artifact_raises(tmp_path):
    art = tmp_path / "positions.edn"
    with pytest.raises(StaleArtifactError, match="does not exist"):
        check_not_stale(art, [])
