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


def test_check_positions_fresh_uses_governance_sources(tmp_path):
    import os
    from scripts._staleness import check_positions_fresh, StaleArtifactError
    ws = tmp_path / "ws"
    (ws / "syntopical").mkdir(parents=True)
    (ws / "rules" / "booklogic").mkdir(parents=True)
    positions = ws / "syntopical" / "positions.edn"
    positions.write_text("{}", encoding="utf-8")
    prov = ws / "rules" / "booklogic" / "induced-theory.prov.edn"
    prov.write_text("{}", encoding="utf-8")
    os.utime(positions, (1000, 1000))
    os.utime(prov, (2000, 2000))
    with pytest.raises(StaleArtifactError):
        check_positions_fresh(positions)
