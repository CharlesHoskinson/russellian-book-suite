# skills/neurosym-forge/tests/test_add_sort.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file
from scripts.add_sort import add_sort

SORTS_KEY = Keyword("sorts")
CHECKSUMS_KEY = Keyword("checksums")


def _seed(tmp_path: Path) -> Path:
    (tmp_path / "rules").mkdir()
    write_edn_file(tmp_path / "rules" / "seed.edn", {
        Keyword("version"): 1,
        SORTS_KEY: [Keyword("int"), Keyword("real")],
        Keyword("rules"): [],
        Keyword("atoms"): [],
    })
    write_edn_file(tmp_path / "rules" / ".checksums.edn", {CHECKSUMS_KEY: {}})
    return tmp_path


def test_appends_primitive(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_sort(project, Keyword("molarity"))
    payload = read_edn_file(project / "rules" / "seed.edn")
    assert Keyword("molarity") in payload[SORTS_KEY]


def test_rejects_duplicate(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    with pytest.raises(ValueError, match="already present"):
        add_sort(project, Keyword("int"))


def test_appends_enum(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_sort(project, {Keyword("kind"): Keyword("enum"),
                       Keyword("members"): [Keyword("sat"), Keyword("unsat"), Keyword("unknown")]})
    payload = read_edn_file(project / "rules" / "seed.edn")
    assert any(isinstance(s, dict) and s.get(Keyword("kind")) == Keyword("enum")
               for s in payload[SORTS_KEY])


def test_updates_checksum(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_sort(project, Keyword("molarity"))
    checksums = read_edn_file(project / "rules" / ".checksums.edn")[CHECKSUMS_KEY]
    assert "seed.edn" in checksums
