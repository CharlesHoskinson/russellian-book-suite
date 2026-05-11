"""Tests for compile_thesis.py."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compile_thesis import compile_thesis  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "tiny-thesis.yaml"


def _make_workspace(tmp_path: Path) -> Path:
    """Lay out a workspace mirroring the real book pipeline."""
    (tmp_path / "thesis").mkdir()
    shutil.copy(FIXTURE, tmp_path / "thesis" / "tiny.yaml")
    return tmp_path


def test_loads_yaml(tmp_path: Path) -> None:
    workspace = _make_workspace(tmp_path)
    with (workspace / "thesis" / "tiny.yaml").open("r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    assert spec["book_id"] == "tiny"
    assert spec["thesis"]["polarity"] == "descriptive"
    assert len(spec["sub_arguments"]) == 2
    assert len(spec["invariants"]) == 1


def test_emits_triples(tmp_path: Path) -> None:
    workspace = _make_workspace(tmp_path)
    result = compile_thesis(workspace, "tiny")
    assert result.sub_arguments == 2
    assert result.invariants == 1
    assert result.output_path == workspace / ".knowledge" / "thesis-triples.ttl"
    text = result.output_path.read_text(encoding="utf-8")
    # Node types present
    assert ":ThesisNode" in text
    assert ":SubArgument" in text
    assert ":Invariant" in text
    # Specific nodes present
    assert ":first-leg" in text
    assert ":second-leg" in text
    assert ":tiny-invariant" in text
    # Edges present
    assert ":supports" in text
    assert ":requiresEvidence" in text
    # Namespace present
    assert "https://russellian.book/thesis/" in text


def test_idempotent(tmp_path: Path) -> None:
    workspace = _make_workspace(tmp_path)
    r1 = compile_thesis(workspace, "tiny")
    first = r1.output_path.read_bytes()
    r2 = compile_thesis(workspace, "tiny")
    second = r2.output_path.read_bytes()
    assert first == second


def test_missing_book(tmp_path: Path) -> None:
    workspace = _make_workspace(tmp_path)
    with pytest.raises(FileNotFoundError):
        compile_thesis(workspace, "nonexistent")
