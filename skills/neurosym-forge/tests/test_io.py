# skills/neurosym-forge/tests/test_io.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file, file_checksum


def test_round_trip(tmp_path: Path) -> None:
    payload = {
        Keyword("sorts"): [Keyword("int"), Keyword("real")],
        Keyword("rules"): [],
        Keyword("atoms"): [],
    }
    out = tmp_path / "atomspace.edn"
    write_edn_file(out, payload)
    back = read_edn_file(out)
    assert back == payload


def test_keywords_render_unquoted(tmp_path: Path) -> None:
    out = tmp_path / "x.edn"
    write_edn_file(out, {Keyword("k"): Keyword("foo")})
    text = out.read_text(encoding="utf-8")
    # Keywords must NOT appear as quoted strings
    assert ":foo" in text
    assert '"foo"' not in text
    assert ":k " in text or ":k\n" in text


def test_checksum_stable(tmp_path: Path) -> None:
    f = tmp_path / "x.edn"
    f.write_text("hello", encoding="utf-8")
    a = file_checksum(f)
    b = file_checksum(f)
    assert a == b
    assert len(a) == 64


def test_checksum_changes_on_edit(tmp_path: Path) -> None:
    f = tmp_path / "x.edn"
    f.write_text("hello", encoding="utf-8")
    a = file_checksum(f)
    f.write_text("hello!", encoding="utf-8")
    b = file_checksum(f)
    assert a != b
