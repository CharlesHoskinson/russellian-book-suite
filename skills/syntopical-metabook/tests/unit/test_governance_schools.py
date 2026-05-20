"""Tests for syntopical/schools/*.edn parsing."""
from __future__ import annotations
from pathlib import Path
import textwrap
import pytest
from scripts.governance._schools import (
    School, SchoolError, load_school, load_schools_dir,
)


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return p


def test_load_school_returns_dataclass(tmp_path):
    f = _write(tmp_path / "praos.edn", """
        {:version 1
         :school :praos
         :name "Praos school"
         :charter "Adaptively-secure Ouroboros family."
         :members ["praos2017" "genesis2018"]
         :canonical-rejects [:tau-multi-leader]
         :canonical-asserts [:tau-leq-one]}
    """)
    s = load_school(f)
    assert isinstance(s, School)
    assert s.slug == "praos"
    assert s.name == "Praos school"
    assert s.members == ["praos2017", "genesis2018"]
    assert ":tau-leq-one" in s.canonical_asserts
    assert ":tau-multi-leader" in s.canonical_rejects


def test_load_school_missing_required_field_raises(tmp_path):
    f = _write(tmp_path / "broken.edn", """
        {:version 1 :name "missing slug"}
    """)
    with pytest.raises(SchoolError, match=":school"):
        load_school(f)


def test_load_school_unknown_version_raises(tmp_path):
    f = _write(tmp_path / "future.edn", """
        {:version 99 :school :x :name "x" :charter "x" :members []}
    """)
    with pytest.raises(SchoolError, match="version"):
        load_school(f)


def test_load_schools_dir_returns_all(tmp_path):
    _write(tmp_path / "schools" / "a.edn",
           '{:version 1 :school :a :name "A" :charter "a" :members []}')
    _write(tmp_path / "schools" / "b.edn",
           '{:version 1 :school :b :name "B" :charter "b" :members []}')
    out = load_schools_dir(tmp_path / "schools")
    assert sorted(s.slug for s in out) == ["a", "b"]


def test_load_schools_dir_missing_directory_returns_empty(tmp_path):
    out = load_schools_dir(tmp_path / "nonexistent")
    assert out == []
