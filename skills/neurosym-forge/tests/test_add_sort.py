# skills/neurosym-forge/tests/test_add_sort.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json, write_json_as_edn
from scripts.add_sort import add_sort


def _seed(tmp_path: Path) -> Path:
    (tmp_path / "rules").mkdir()
    write_json_as_edn(tmp_path / "rules" / "seed.edn",
                      {"version": 1, "sorts": [":int", ":real"], "rules": [], "atoms": []})
    write_json_as_edn(tmp_path / "rules" / ".checksums.edn",
                      {"checksums": {}})
    return tmp_path


def test_appends_primitive(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_sort(project, ":molarity")
    payload = read_edn_as_json(project / "rules" / "seed.edn")
    assert ":molarity" in payload["sorts"]


def test_rejects_duplicate(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    with pytest.raises(ValueError, match="already present"):
        add_sort(project, ":int")


def test_appends_enum(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_sort(project, {"kind": "enum", "members": [":sat", ":unsat", ":unknown"]})
    payload = read_edn_as_json(project / "rules" / "seed.edn")
    assert any(isinstance(s, dict) and s.get("kind") == "enum" for s in payload["sorts"])


def test_updates_checksum(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_sort(project, ":molarity")
    checksums = read_edn_as_json(project / "rules" / ".checksums.edn")["checksums"]
    assert "seed.edn" in checksums
